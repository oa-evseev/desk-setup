# desk-setup

`desk-setup` launches applications and arranges their windows from a
declarative YAML configuration.

It currently supports KDE Plasma on Wayland through KWin. Monitors can
be addressed by their output name or by logical names such as `left`,
`center`, and `right`. Windows can be placed using presets including
`full`, `left`, `right`, and the four screen corners.

## Requirements

- Linux with KDE Plasma on Wayland;
- Python 3 with the `venv` module;
- `qdbus6` or `qdbus`.

## Installation

Clone the repository and run the user-level installer:

```sh
git clone https://github.com/oa-evseev/desk-setup.git
cd desk-setup
./install.sh
```

No `sudo` is required. The installer creates:

- the application and its virtual environment in
  `~/.local/share/desk-setup`;
- the `desk-setup` command in `~/.local/bin`;
- editable configurations in `~/.config/desk-setup`.

Existing configurations are preserved when the installer is run again.
To update the installed application:

```sh
git pull
./install.sh
```

If `~/.local/bin` is not in `PATH`, add it to your shell configuration.

## Usage

List the installed configurations:

```sh
desk-setup list
```

Apply one by name:

```sh
desk-setup coding
```

The explicit `apply` form and direct paths are also accepted:

```sh
desk-setup apply coding
desk-setup ~/my-desk.yaml
```

A configuration describes which applications belong on each monitor:

```yaml
version: 1

monitors:
  left:
    windows:
      - exec:
          - firefox
          - --new-window
          - https://app.todoist.com/app/today
        tile: left
        after:
          - exec:
              - firefox
              - --new-tab
              - https://chatgpt.com

      - exec:
          - konsole
        cwd: ~/projects
        tile: right
```

Each window supports:

- `exec`: command and arguments used to launch the application;
- `tile`: `full`, `left`, `right`, `top`, `bottom`, or one of
  `top-left`, `top-right`, `bottom-left`, and `bottom-right`;
- `cwd`: optional working directory;
- `after`: optional commands run after the main window has appeared,
  been arranged, and activated.

An `after` command can specify its own `cwd`; otherwise it inherits the
main window's working directory. This is useful when an application
needs a second command after its window becomes active, such as opening
another Firefox tab in the newly created window.

Edit `~/.config/desk-setup/coding.yaml` to match your applications,
monitor names, and working directories. See
[`examples/coding.yaml`](examples/coding.yaml) for the source example.

## Uninstallation

Remove the application and command while preserving user configurations:

```sh
~/.local/share/desk-setup/uninstall.sh
```

Remove the application and all user configurations:

```sh
~/.local/share/desk-setup/uninstall.sh --purge
```

## Development

```sh
make env
make test
```

## License

See [`LICENSE`](LICENSE).
