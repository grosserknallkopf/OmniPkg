# Security Policy

OmniPkg is a desktop package-management frontend. It can start native package
managers, optional sudo or polkit flows, and manual installers, so security
reports are taken seriously even while the project is young.

## Supported Versions

Security fixes are made on the `main` branch. Until OmniPkg has tagged stable
releases, please treat the latest `main` commit as the only supported version.

## Reporting a Vulnerability

Please do not open a public issue for a suspected vulnerability.
Use GitHub's private vulnerability reporting for this repository.

Useful reports include:

- the affected OmniPkg commit or version
- your distribution and desktop environment
- the package source involved, such as APT, Flatpak, npm, pipx, or manual
  archive install
- exact reproduction steps
- whether elevated privileges were requested
- expected and actual behavior

## Security Boundaries

OmniPkg is not a sandbox. It delegates installation, removal, refresh, and
update operations to the package managers already installed on the system.
Those tools keep their normal trust model, prompts, repositories, signatures,
and side effects.

OmniPkg intentionally runs as a normal user. When system package managers need
administrator rights, OmniPkg uses `pkexec`, `sudo -A`, or `sudo` depending on
what the system provides. The optional installer-created sudoers rule should be
reviewed before use and can be skipped with `./install.sh --no-sudoers`.

Manual archive and AppImage installs are convenience features, not a trust
decision. Only install files from sources you trust. OmniPkg rejects archive
paths and links that try to escape the extraction directory, but it does not
audit the software inside an archive.

OmniPkg does not collect telemetry and does not require project-specific
credentials. It may run external package-manager commands that contact their
configured repositories.
