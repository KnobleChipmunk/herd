import datetime

import pytest
import yaml

import bindings
import herdsetup as setup

TODAY = datetime.date(2026, 9, 27)
RECS = {"version": 1, "roles": {
    "builder": [{"harness": "pi", "provider": "ollama", "model": "swift15-qwen3.8-128k:latest",
                 "reason": "local, no quota", "source": "observed", "date": "2026-09-27"},
                {"harness": "claude", "model": "sonnet", "reason": "reliable edits", "source": "preference",
                 "date": "2026-09-27"}],
    "build_reviewer": [{"harness": "codex", "model": "gpt-6-sol", "reason": "one-round clean reviews",
                        "source": "observed", "date": "2026-08-25"},
                       {"harness": "claude", "model": "fable", "reason": "a model other than the builder's",
                        "source": "preference", "date": "2026-09-27"}]}}


def only(*harnesses):
    return lambda binary: f"/bin/{binary}" if binary in harnesses else None


def scripted(*answers):
    """An input() that returns the scripted answers in order and records every prompt."""
    it = iter(answers)
    prompts = []

    def ask(prompt):
        prompts.append(prompt)
        return next(it)

    ask.prompts = prompts
    return ask


# --- discovery ----------------------------------------------------------------

def test_discovery_finds_only_installed_supported_harnesses():
    assert setup.discover(only("claude")) == ["claude"]
    assert setup.discover(only("claude", "codex", "pi")) == ["claude", "codex", "pi"]
    assert setup.discover(only()) == []


# --- recommendations (U6) -------------------------------------------------------

def test_the_shipped_recommendations_file_is_valid():
    assert setup.validate_recommendations(setup.load_recommendations()) == []


@pytest.mark.parametrize("entry, error", [
    ({"harness": "claude", "model": "x", "source": "observed", "date": "2026-09-27"}, "missing reason"),
    ({"harness": "claude", "model": "x", "reason": "r", "source": "benchmark", "date": "2026-09-27"},
     "source must be one of official, preference, observed"),
    ({"harness": "claude", "model": "x", "reason": "r", "source": "observed"}, "missing date"),
])
def test_every_recommendation_needs_a_reason_a_source_type_and_a_date(entry, error):
    errors = setup.validate_recommendations({"version": 1, "roles": {"builder": [entry]}})
    assert any(error in e for e in errors)


def test_recommendations_are_limited_to_the_usable_pool_and_flag_stale_ones():
    offers = setup.offers("build_reviewer", RECS, ["claude"], today=TODAY, stale_days=30)
    assert [(o["harness"], o["model"]) for o in offers] == [("claude", "fable")]
    stale = setup.offers("build_reviewer", RECS, ["codex"], today=TODAY, stale_days=30)
    assert stale[0]["stale"] is True
    assert setup.offers("designer", RECS, ["claude"], today=TODAY) == []


# --- assisted setup (U4) --------------------------------------------------------

def test_a_claude_only_machine_is_asked_per_role_and_warned_about_same_models(capsys):
    ask = scripted("claude opus", "1", "claude sonnet", "claude sonnet", "n", "y")
    doc = setup.assisted(RECS, which=only("claude"), existing=None, ask=ask, today=TODAY)
    out = capsys.readouterr().out
    assert [p.split(":")[0] for p in ask.prompts[:4]] == ["lead", "builder", "plan_reviewer", "build_reviewer"]
    assert {b["harness"] for b in doc["roles"].values()} == {"claude"}
    assert doc["roles"]["builder"] == {"harness": "claude", "model": "sonnet"}
    assert "WARNING builder -> build_reviewer: same model (sonnet)" in out
    assert doc["probe_consent"] is False
    assert bindings.validate(doc) == []


def test_the_consent_question_names_its_cost():
    ask = scripted("claude opus", "claude sonnet", "claude fable", "claude fable", "y", "y")
    doc = setup.assisted(RECS, which=only("claude"), existing=None, ask=ask, today=TODAY)
    consent = ask.prompts[4]
    assert "one short diagnostic request per selected binding" in consent and "quota" in consent
    assert doc["probe_consent"] is True


def test_nothing_is_saved_without_confirmation(tmp_path, capsys):
    target = tmp_path / "bindings.yaml"
    ask = scripted("claude opus", "claude sonnet", "claude fable", "claude fable", "n", "n")
    assert setup.run_assisted(RECS, target, which=only("claude"), ask=ask, today=TODAY) == 1
    assert not target.exists()
    assert "version: 1" in capsys.readouterr().out  # the preview was shown


def test_a_confirmed_setup_is_written_and_reloads(tmp_path):
    target = tmp_path / "herd" / "bindings.yaml"
    ask = scripted("claude opus", "claude sonnet", "claude fable", "claude fable", "n", "y")
    assert setup.run_assisted(RECS, target, which=only("claude"), ask=ask, today=TODAY) == 0
    assert bindings.load(target)["roles"]["lead"] == {"harness": "claude", "model": "opus"}


def test_a_saved_choice_is_the_default_and_rediscovery_never_overrides_it(tmp_path):
    target = tmp_path / "bindings.yaml"
    target.write_text(yaml.safe_dump({"version": 1, "roles": {"builder": {"harness": "pi", "provider": "ollama",
                                                                          "model": "saved-model"}}}))
    ask = scripted("claude opus", "", "claude fable", "claude fable", "n", "y")
    setup.run_assisted(RECS, target, which=only("claude", "pi"), ask=ask, today=TODAY)
    assert "[saved: pi saved-model]" in ask.prompts[1]
    assert bindings.load(target)["roles"]["builder"] == {"harness": "pi", "provider": "ollama", "model": "saved-model"}


def test_an_unusable_answer_is_asked_again():
    ask = scripted("codex gpt-6-sol", "claude opus", "claude sonnet", "claude fable", "claude fable", "n", "y")
    doc = setup.assisted(RECS, which=only("claude"), existing=None, ask=ask, today=TODAY)
    assert ask.prompts[1].startswith("lead") and doc["roles"]["lead"]["model"] == "opus"


# --- headless validation ----------------------------------------------------------

def test_validate_lists_what_is_missing_without_prompting(tmp_path, capsys):
    target = tmp_path / "bindings.yaml"
    assert setup.validate_machine(target, which=only("claude")) == 1
    assert "no bindings file" in capsys.readouterr().out
    target.write_text(yaml.safe_dump({"version": 1, "roles": {
        "lead": {"harness": "claude", "model": "opus"}, "builder": {"harness": "pi", "model": "m"}}}))
    assert setup.validate_machine(target, which=only("claude")) == 1
    out = capsys.readouterr().out
    assert "builder: pi is not installed" in out
    assert "plan_reviewer: not bound" in out and "build_reviewer: not bound" in out


def test_a_complete_machine_validates(tmp_path, capsys):
    target = tmp_path / "bindings.yaml"
    target.write_text(yaml.safe_dump({"version": 1, "roles": {
        r: {"harness": "claude", "model": m} for r, m in
        (("lead", "opus"), ("builder", "sonnet"), ("plan_reviewer", "fable"), ("build_reviewer", "fable"))}}))
    assert setup.validate_machine(target, which=only("claude")) == 0
    assert "ok" in capsys.readouterr().out


def test_from_example_copies_the_profile_only_after_confirmation(tmp_path):
    target = tmp_path / "bindings.yaml"
    assert setup.from_example(target, ask=scripted("n")) == 1 and not target.exists()
    assert setup.from_example(target, ask=scripted("y")) == 0
    assert bindings.load(target)["roles"]["builder"]["harness"] == "codex"
    assert setup.from_example(target, ask=scripted("y")) == 1  # never overwrites an existing file


# --- plan review #39 round 1 -------------------------------------------------

def test_a_local_only_machine_can_bind_every_role_with_a_custom_model(tmp_path):
    ask = scripted("pi m1 provider=ollama", "pi m2 provider=ollama", "pi m3 provider=ollama", "pi m4 provider=ollama",
                   "n", "y")
    target = tmp_path / "b.yaml"
    assert setup.run_assisted(RECS, target, which=only("pi"), ask=ask, today=TODAY) == 0
    roles = bindings.load(target)["roles"]
    assert roles["lead"] == {"harness": "pi", "model": "m1", "provider": "ollama"}
    assert roles["build_reviewer"]["model"] == "m4"


def test_a_typed_field_the_adapter_cannot_honor_is_asked_again(capsys):
    ask = scripted("claude opus provider=bedrock", "claude opus", "claude sonnet", "claude fable", "claude fable", "n")
    doc = setup.assisted(RECS, which=only("claude"), existing=None, ask=ask, today=TODAY)
    assert doc["roles"]["lead"] == {"harness": "claude", "model": "opus"}
    assert "does not support provider" in capsys.readouterr().out


def test_an_invalid_recommendation_is_left_out_with_a_reason(capsys):
    recs = {"version": 1, "roles": {"lead": [
        {"harness": "codex", "model": "x", "endpoint": "http://localhost:9999", "reason": "r", "source": "observed",
         "date": "2026-09-27"},
        {"harness": "codex", "model": "y", "reason": "r", "source": "observed", "date": "2026-09-27"}]}}
    ask = scripted("1", "codex a", "codex b", "codex c", "n")
    doc = setup.assisted(recs, which=only("codex"), existing=None, ask=ask, today=TODAY)
    assert doc["roles"]["lead"] == {"harness": "codex", "model": "y"}
    assert "recommendation lead 1 left out" in capsys.readouterr().out


def test_a_machine_with_no_supported_harness_ends_without_prompting(tmp_path, capsys):
    def never(prompt):
        raise AssertionError(f"prompted: {prompt}")
    target = tmp_path / "b.yaml"
    assert setup.run_assisted(RECS, target, which=only(), ask=never, today=TODAY) == 1
    assert not target.exists() and "no supported harness" in capsys.readouterr().out


def test_every_pairs_diversity_is_shown_before_the_consent_question(capsys):
    answers = iter(["claude opus", "claude sonnet", "claude fable", "claude fable", "n"])
    at_consent = {}

    def ask(prompt):
        if prompt == setup.CONSENT:
            at_consent["out"] = capsys.readouterr().out  # what was shown BEFORE the question
        return next(answers)

    setup.assisted(RECS, which=only("claude"), existing=None, ask=ask, today=TODAY)
    out = at_consent["out"]
    assert "builder -> build_reviewer: different model" in out
    assert "lead -> plan_reviewer: different model" in out
    assert "builder -> qa: unknown model" in out
    assert "selected:" in out and "lead: claude opus" in out


@pytest.mark.parametrize("doc", [None, [], {"version": 1, "roles": []}, {"version": 1, "roles": {"lead": {}}},
                                 {"version": 1, "roles": {"lead": ["x"]}},
                                 {"version": 1, "roles": {"lead": [{"harness": ["codex"], "model": "m"}]}}])
def test_a_malformed_recommendations_document_is_diagnosed_not_crashed_on(doc):
    assert setup.validate_recommendations(doc)


def test_malformed_recommendation_yaml_is_ignored_with_a_reason(tmp_path, capsys):
    f = tmp_path / "r.yaml"
    f.write_text("roles: [\n")
    recs = setup.load_recommendations(f)
    assert recs == {"version": 1, "roles": {}} and "is not valid YAML" in capsys.readouterr().out


def test_a_role_left_empty_in_the_recommendations_still_allows_typed_setup(capsys):
    recs = {"version": 1, "roles": {"lead": None}}
    assert setup.validate_recommendations(recs) == []
    ask = scripted("claude opus", "claude sonnet", "claude fable", "claude fable", "n")
    doc = setup.assisted(recs, which=only("claude"), existing=None, ask=ask, today=TODAY)
    assert doc["roles"]["lead"] == {"harness": "claude", "model": "opus"}
    assert "lead: no recommendation for the installed harnesses (unknown)" in capsys.readouterr().out


# --- build review #39 round 1 -------------------------------------------------

def test_a_bad_entry_is_left_out_while_valid_entries_are_still_offered(capsys):
    recs = {"version": 1, "roles": {"lead": [
        {"harness": "claude", "model": "x", "source": "observed", "date": "2026-09-27"},
        {"harness": "claude", "model": "y", "reason": "r", "source": "observed", "date": "2026-09-27"}]}}
    ask = scripted("1", "claude sonnet", "claude fable", "claude fable", "n")
    doc = setup.assisted(recs, which=only("claude"), existing=None, ask=ask, today=TODAY)
    assert doc["roles"]["lead"] == {"harness": "claude", "model": "y"}
    assert "recommendation lead 1 left out" in capsys.readouterr().out


def test_from_example_does_not_even_ask_when_the_file_exists(tmp_path):
    target = tmp_path / "bindings.yaml"
    target.write_text("keep me")

    def never(prompt):
        raise AssertionError(f"prompted: {prompt}")

    assert setup.from_example(target, ask=never) == 1
    assert target.read_text() == "keep me"


def test_an_entry_without_a_date_is_left_out_without_crashing(capsys):
    recs = {"version": 1, "roles": {"lead": [
        {"harness": "claude", "model": "x", "reason": "r", "source": "observed"},
        {"harness": "claude", "model": "y", "reason": "r", "source": "observed", "date": "2026-09-27"}]}}
    ask = scripted("1", "claude sonnet", "claude fable", "claude fable", "n")
    doc = setup.assisted(recs, which=only("claude"), existing=None, ask=ask, today=TODAY)
    assert doc["roles"]["lead"] == {"harness": "claude", "model": "y"}
    assert "recommendation lead 1 left out" in capsys.readouterr().out


def test_from_example_creates_the_target_directory_after_confirmation(tmp_path):
    target = tmp_path / "herd" / "bindings.yaml"
    assert setup.from_example(target, ask=scripted("y")) == 0
    assert bindings.load(target)["roles"]["builder"]["harness"] == "codex"


def test_from_example_never_clobbers_a_file_created_during_confirmation(tmp_path):
    target = tmp_path / "bindings.yaml"

    def ask(prompt):
        target.write_text("keep me")
        return "y"

    assert setup.from_example(target, ask=ask) == 1
    assert target.read_text() == "keep me"

