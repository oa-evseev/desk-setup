import os
import subprocess
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def make_fake_system_tools(tmp_path: Path) -> Path:
    bin_dir = tmp_path / "fake-bin"
    bin_dir.mkdir()

    python = bin_dir / "python3"
    python.write_text(
        """#!/usr/bin/env bash
set -e
if [[ "$1" == "-m" && "$2" == "venv" ]]; then
    venv="$3"
    mkdir -p "$venv/bin"
    cat > "$venv/bin/python" <<'EOF'
#!/usr/bin/env bash
exit 0
EOF
    chmod +x "$venv/bin/python"
    exit 0
fi
exit 1
""",
        encoding="utf-8",
    )
    python.chmod(0o755)

    qdbus = bin_dir / "qdbus6"
    qdbus.write_text("#!/usr/bin/env bash\nexit 0\n", encoding="utf-8")
    qdbus.chmod(0o755)

    return bin_dir


def installer_environment(tmp_path: Path) -> dict[str, str]:
    fake_bin = make_fake_system_tools(tmp_path)
    environment = os.environ.copy()
    environment.update(
        {
            "HOME": str(tmp_path / "home"),
            "XDG_DATA_HOME": str(tmp_path / "data"),
            "XDG_CONFIG_HOME": str(tmp_path / "config"),
            "XDG_BIN_HOME": str(tmp_path / "bin"),
            "PATH": f"{fake_bin}:{environment['PATH']}",
        }
    )
    return environment


def run_script(name: str, environment: dict[str, str], *arguments: str):
    return subprocess.run(
        [str(PROJECT_ROOT / name), *arguments],
        cwd=PROJECT_ROOT,
        env=environment,
        check=True,
        capture_output=True,
        text=True,
    )


def complete(
    environment: dict[str, str],
    completion: Path,
    *words: str,
) -> list[str]:
    assignments = " ".join(
        f"COMP_WORDS[{index}]={word!r}"
        for index, word in enumerate(words)
    )
    result = subprocess.run(
        [
            "bash",
            "-c",
            (
                f"source {str(completion)!r}; "
                f"{assignments}; "
                f"COMP_CWORD={len(words) - 1}; "
                "_desk_setup; "
                'printf "%s\\n" "${COMPREPLY[@]}"'
            ),
        ],
        env=environment,
        check=True,
        capture_output=True,
        text=True,
    )
    return result.stdout.splitlines()


def test_install_creates_application_wrapper_completion_and_initial_config(
    tmp_path,
):
    environment = installer_environment(tmp_path)

    result = run_script("install.sh", environment)

    app_dir = tmp_path / "data" / "desk-setup"
    wrapper = tmp_path / "bin" / "desk-setup"
    completion = (
        tmp_path
        / "data"
        / "bash-completion"
        / "completions"
        / "desk-setup"
    )
    config = tmp_path / "config" / "desk-setup" / "coding.yaml"
    assert (app_dir / "src" / "main.py").is_file()
    assert (app_dir / ".venv" / "bin" / "python").is_file()
    assert os.access(app_dir / "uninstall.sh", os.X_OK)
    assert wrapper.is_file()
    assert os.access(wrapper, os.X_OK)
    assert completion.is_file()
    assert config.read_text(encoding="utf-8") == (
        PROJECT_ROOT / "examples" / "coding.yaml"
    ).read_text(encoding="utf-8")
    assert "Installation complete" in result.stdout


def test_completion_offers_commands_and_configurations_dynamically(tmp_path):
    environment = installer_environment(tmp_path)
    run_script("install.sh", environment)
    completion = (
        tmp_path
        / "data"
        / "bash-completion"
        / "completions"
        / "desk-setup"
    )
    config_dir = tmp_path / "config" / "desk-setup"
    (config_dir / "deep work.yaml").write_text(
        "version: 1\n",
        encoding="utf-8",
    )
    (config_dir / "gaming.yaml").write_text("version: 1\n", encoding="utf-8")
    (config_dir / "notes.txt").write_text("ignored\n", encoding="utf-8")

    assert complete(
        environment,
        completion,
        "desk-setup",
        "",
    ) == ["coding", "deep work", "gaming", "help", "list"]
    assert complete(
        environment,
        completion,
        "desk-setup",
        "ga",
    ) == ["gaming"]
    assert complete(
        environment,
        completion,
        "desk-setup",
        "apply",
        "",
    ) == ["coding", "deep work", "gaming"]


def test_reinstall_does_not_overwrite_user_configuration(tmp_path):
    environment = installer_environment(tmp_path)
    run_script("install.sh", environment)
    config = tmp_path / "config" / "desk-setup" / "coding.yaml"
    config.write_text("user changes\n", encoding="utf-8")

    run_script("install.sh", environment)

    assert config.read_text(encoding="utf-8") == "user changes\n"


def test_reinstall_does_not_restore_example_when_another_config_exists(
    tmp_path,
):
    environment = installer_environment(tmp_path)
    run_script("install.sh", environment)
    config_dir = tmp_path / "config" / "desk-setup"
    (config_dir / "personal.yaml").write_text(
        "version: 1\nmonitors: {}\n",
        encoding="utf-8",
    )
    (config_dir / "coding.yaml").unlink()

    run_script("install.sh", environment)

    assert not (config_dir / "coding.yaml").exists()
    assert (config_dir / "personal.yaml").is_file()


def test_uninstall_preserves_configuration_by_default(tmp_path):
    environment = installer_environment(tmp_path)
    run_script("install.sh", environment)

    result = run_script("uninstall.sh", environment)

    assert not (tmp_path / "data" / "desk-setup").exists()
    assert not (tmp_path / "bin" / "desk-setup").exists()
    assert not (
        tmp_path
        / "data"
        / "bash-completion"
        / "completions"
        / "desk-setup"
    ).exists()
    assert (tmp_path / "config" / "desk-setup" / "coding.yaml").is_file()
    assert "preserved" in result.stdout


def test_uninstall_purge_removes_configuration(tmp_path):
    environment = installer_environment(tmp_path)
    run_script("install.sh", environment)

    run_script("uninstall.sh", environment, "--purge")

    assert not (tmp_path / "data" / "desk-setup").exists()
    assert not (tmp_path / "bin" / "desk-setup").exists()
    assert not (tmp_path / "config" / "desk-setup").exists()


def test_uninstall_rejects_unknown_argument(tmp_path):
    environment = installer_environment(tmp_path)

    result = subprocess.run(
        [str(PROJECT_ROOT / "uninstall.sh"), "--everything"],
        cwd=PROJECT_ROOT,
        env=environment,
        capture_output=True,
        text=True,
    )

    assert result.returncode != 0
    assert "Usage:" in result.stderr
