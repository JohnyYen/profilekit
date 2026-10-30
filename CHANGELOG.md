# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/) once it
reaches its first tagged release.

## [Unreleased]

### Added

- `git-repo` publisher kind: `profile publish --execute` commits and pushes
  generated artifacts (text or binary) into another git repository, such as a
  GitHub profile README, a CV repository or a portfolio. It plans against a
  shallow clone, never makes an empty commit, refuses to overwrite files edited
  outside profilekit unless `on_conflict = "overwrite"`, and rejects
  credentials embedded in an http(s) `repo` URL.

### Changed

- Renamed the distributed package from the non-redistributable `generators`
  top-level module to `profilekit`, moved to a `src/` layout, and declared
  full PyPI-publishable metadata (`description`, `license`, `authors`,
  `classifiers`, `project.urls`).
- Packaged JSON Schema files as installed package data so a `pip install`ed
  copy of the tool can validate data without a git checkout.
- Added legal and community files (`LICENSE`, `CONTRIBUTING.md`,
  `CODE_OF_CONDUCT.md`, `SECURITY.md`) ahead of the open-source release.
