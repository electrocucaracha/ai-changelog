<!-- Markdownlint-disable MD024 -->

# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

<!-- markdownlint-disable MD024 -->
<!-- markdownlint-disable MD013 -->

## [Unreleased]

## [9.2.2] - 2026-08-22

### Changed

- Simplified the print statement for mutation totals to use a single f-string, improving code clarity and consistency with modern Python formatting practices without affecting functional behavior. [1032f70a](https://github.com/electrocucaracha/ai-changelog/commit/1032f70a531bb1d07fd25eb587905dd2e122ab67)

## [9.2.1] - 2026-08-22

### Changed

- Enabled scheduled and on-demand quality improvements with minimal manual intervention, supporting long-term maintainability. [d0ad29f6](https://github.com/electrocucaracha/ai-changelog/commit/d0ad29f680584d9b8396f2bd6c72a640b5ac8602)

## [9.2.0] - 2026-08-22

### Added

- BREAKING: Hardened the Ollama model validation to ensure readiness before processing, causing the CLI to exit early if the model is missing or the API is unreachable and requiring downstream tools to adjust their workflows due to the breaking behavior. [79ed6b56](https://github.com/electrocucaracha/ai-changelog/commit/79ed6b562436a5cbbc3a1810b9e98a006acf015b)

## [9.1.0] - 2026-08-22

### Added

- Enabled detailed changelog entries for versions 8.8.0 through 8.11.0, improving transparency and providing a comprehensive history of recent changes for users and contributors. [87102909](https://github.com/electrocucaracha/ai-changelog/commit/87102909550602dca7e2de54652d5c020b7282a3)

## [9.0.0] - 2026-08-22

### Removed

- Streamlined the release process by removing unnecessary ollama cache and leveraging the GitHub CLI for improved maintainability and reduced reliance on third-party actions. [cee41c83](https://github.com/electrocucaracha/ai-changelog/commit/cee41c8398cbfcc562bdf2109eb3cd8c1d72725c)

## [8.7.0] - 2026-08-21

### Added

- Enabled comprehensive release history for users and contributors with detailed changelog entries for versions 8.4.0 through 8.7.1, reflecting recent automation, CI enhancements, and optimizations to release note generation. [48768c8d](https://github.com/electrocucaracha/ai-changelog/commit/48768c8d3d68dda0c6b0ac43a1c395946de43f88)

## [8.6.3] - 2026-08-21

### Changed

- Enhanced workflow security and isolation by disabling credential persistence and explicitly setting up Git authentication, while also preventing cache collisions across different projects. [05bba30d](https://github.com/electrocucaracha/ai-changelog/commit/05bba30d647e2c8d205bf4939cc8044aa2a603da)

## [8.6.2] - 2026-08-21

### Changed

- Streamlined the release process by delegating model selection to downstream tools and enabling the changelog commit step to continue on error. [a1878b14](https://github.com/electrocucaracha/ai-changelog/commit/a1878b146a027a065223b78413b19fe7c9cb814d)

## [8.6.1] - 2026-08-21

### Fixed

- Simplified the release process by extracting only the latest two changelog entries into the release body. [507f7fb4](https://github.com/electrocucaracha/ai-changelog/commit/507f7fb46236777b93df50d5d51a816bb2b5a979)

## [8.6.0] - 2026-08-21

### Added

- Stabilized release notes by automatically trimming the changelog to the latest three entries before each release, ensuring concise and manageable release artifacts. [bc26321c](https://github.com/electrocucaracha/ai-changelog/commit/bc26321c3e8bf12781e92f03293603cd87284037)

## [8.5.0] - 2026-08-21

### Added

- Enabled detailed changelog entries for versions 7.5.0 through 8.3.2, covering new features, optimizations, dependency updates, and documentation improvements, ensuring users and contributors have a comprehensive and accurate history of recent changes. [6c5a62de](https://github.com/electrocucaracha/ai-changelog/commit/6c5a62de3007579b7c77193916e35b0655c062a0)

## [8.4.2] - 2026-08-21

### Changed

- Upgraded multiple dependencies to their latest versions to ensure continued compatibility with upstream packages and incorporate recent bugfixes, with no breaking changes expected but downstream consumers should verify integration tests for any subtle behavioral changes. [f475693c](https://github.com/electrocucaracha/ai-changelog/commit/f475693c0c187ef6e42f88aa883c2bbb77590367)

## [8.4.1] - 2026-08-21

### Changed

- Updated the CI workflows' dependencies to ensure a secure and up-to-date environment by upgrading the uv GitHub Action to v10.0.1 and raising the Go version in linter and update workflows to 1.27. [74d74d60](https://github.com/electrocucaracha/ai-changelog/commit/74d74d601735a185bd80e1312243dcc6d8e066ee)

## [8.4.0] - 2026-08-21

### Added

- Enabled write access to workflows for the release workflow, ensuring that actions modifying or triggering other workflows can proceed without interruption. [2e249701](https://github.com/electrocucaracha/ai-changelog/commit/2e2497016bc959b2fac80bc06c1b02af3a393606)

## [8.3.2] - 2026-08-21

### Changed

- Enabled GitHub Actions workflows to properly attribute commits and enabled parallel changelog generation, resulting in improved performance for larger repositories with no impact on release logic. [c4813bfb](https://github.com/electrocucaracha/ai-changelog/commit/c4813bfbb31804fd723a1d4ab826745c435ff372)

## [8.3.1] - 2026-08-21

### Changed

- Optimized the changelog generation workflow to use a locally run Llama 3.1 8B model and cache model data between runs, reducing reliance on external APIs and improving reproducibility. [60e2bdaa](https://github.com/electrocucaracha/ai-changelog/commit/60e2bdaa5e01a635d39d984a31687af89b9f18d1)

## [8.3.0] - 2026-08-21

### Added

- Automated release notes are now generated for each version, streamlining the release process and ensuring consistent, informative release notes. [dd215b4b](https://github.com/electrocucaracha/ai-changelog/commit/dd215b4b00ef134841edc4a9f8d22b6258b46815)

## [8.2.1] - 2026-08-21

### Changed

- Updated dependencies to incorporate the latest bugfixes and compatibility improvements, and to enable new commit message features, maintaining compatibility with upstream tools and improving pre-commit hook reliability. [81f82a15](https://github.com/electrocucaracha/ai-changelog/commit/81f82a15b2e169575637a41979807305d461fef0)

## [8.2.0] - 2026-08-21

### Added

- Enabled project sponsorship links for users to support ongoing development via GitHub Sponsors and Buy Me a Coffee, with no impact on application functionality. [7b2df1c1](https://github.com/electrocucaracha/ai-changelog/commit/7b2df1c1ffef3fac6d447ddde9bc9833d70c33e3)

## [8.1.2] - 2026-08-20

### Changed

- Resolved the broken link to the how-it-works explanation in the custom providers guide, ensuring readers can access the explanation directly without confusion. [14296766](https://github.com/electrocucaracha/ai-changelog/commit/142967667ab2b7f615ad7f0da5369efba71481f7)

## [8.1.1] - 2026-08-20

### Changed

- Simplified test suite configuration for custom AI providers by extracting a reusable helper function and improving assertion specificity for log messages and provider registration. [3c87c798](https://github.com/electrocucaracha/ai-changelog/commit/3c87c798f81b022883507f4e96dd3afb76dd1d25)

## [8.1.0] - 2026-08-19

### Added

- Enabled users to add new LLM backends without modifying the upstream project by introducing a plugin system for custom LiteLLM providers via Python entry points. [1e6ddf1d](https://github.com/electrocucaracha/ai-changelog/commit/1e6ddf1d52b1bf87a2acaf3040b1315a398febab)

## [8.0.2] - 2026-08-15

### Changed

- Documentation pages now use YAML front matter to define titles, navigation order, and parent-child relationships, enabling richer navigation menus and consistent page metadata. [135d50c8](https://github.com/electrocucaracha/ai-changelog/commit/135d50c8e9ed92cf5f69edcff20756a164b70cbb)

## [8.0.1] - 2026-08-15

### Changed

- Clarified the value proposition and benefits of using the AI Changelog Generator, and introduced a system architecture diagram to help new users quickly understand how the tool works, thereby improving onboarding for first-time users. [a896e39c](https://github.com/electrocucaracha/ai-changelog/commit/a896e39c6e22c1b8a12a3ab0ac7b1fde999a0f7f)

## [8.0.0] - 2026-08-13

### Removed

- Simplified the codebase by removing redundant internal helpers and their associated unit tests, without affecting CLI behavior or output. [3fa8bee6](https://github.com/electrocucaracha/ai-changelog/commit/3fa8bee6bb9807fdc0769dd1581f0e1d0cd57fda)

## [7.5.0] - 2026-08-12

### Added

- Enabled detailed changelog entries for releases 7.1.0 to 7.4.3, providing a clear and comprehensive history of recent changes that makes it easier for users and contributors to track project evolution. [2482cbf5](https://github.com/electrocucaracha/ai-changelog/commit/2482cbf5564880c1350a725bb60493de57d8d7fb)

## [7.4.3] - 2026-08-12

### Fixed

- The Makefile's fmt target now reliably installs textlint dependencies globally, resolving issues for users without write permissions, and may prompt for a password on systems with sudo configured. [c1516a3b](https://github.com/electrocucaracha/ai-changelog/commit/c1516a3bb212362bf51cd9669faf7bd116646930)

## [7.4.2] - 2026-08-12

### Changed

- Clarified the contribution guide setup instructions to accurately reflect the correct sequence of steps, starting from 1. [a0affb67](https://github.com/electrocucaracha/ai-changelog/commit/a0affb67818e15206238984a2fd490d2f7b6c79d)

## [7.4.1] - 2026-08-12

### Changed

- Simplified the summary generation logic in CLI tests to reduce repetition and improve maintainability, introducing a centralized helper to customize the returned summary result per test without altering test behavior. [c1c9ad8b](https://github.com/electrocucaracha/ai-changelog/commit/c1c9ad8b361c86366573657d02d868ec800d95b5)

## [7.4.0] - 2026-08-12

### Added

- Enabled the final rendering stage to group and render changelog entries without additional model calls or diff hydration by persisting precomputed changelog entries and summaries as versioned Git notes. [6f46ce60](https://github.com/electrocucaracha/ai-changelog/commit/6f46ce60a60d612581c631df45fc7f91c5cc367b)

## [7.3.1] - 2026-08-12

### Fixed

- The Makefile's fmt target now reliably formats code across environments by ensuring the globally installed textlint and its terminology rule are available. [c44e09ad](https://github.com/electrocucaracha/ai-changelog/commit/c44e09ad6608395afc33c735eca6481f02f24f95)

## [7.3.0] - 2026-08-10

### Added

- Enabled consistent code formatting across the project with the introduction of biome.json, which specifies an indentation style of 2 spaces using spaces. [97e1baa7](https://github.com/electrocucaracha/ai-changelog/commit/97e1baa7317117f94182c04870fb0811eff565d0)

## [7.2.0] - 2026-08-10

### Added

- Enabled textlint with autofix to enforce consistent prose style and terminology across the project, improving documentation quality and readability with no impact on code execution. [fe2ef3ce](https://github.com/electrocucaracha/ai-changelog/commit/fe2ef3ce3f65a21b4c086c164abc9c53ad04257b)

## [7.1.0] - 2026-08-10

### Added

- Enabled comprehensive changelog entries for versions 5.1.1 through 7.0.0, providing users with a clear history of changes, enhancements, and bugfixes across recent versions. [6b5f283c](https://github.com/electrocucaracha/ai-changelog/commit/6b5f283c314462dbe9bd449241a2c71fbb3a1bfc)

## [7.0.0] - 2026-08-10

### Removed

- Simplified the CI pipeline by eliminating the non-essential reporting feature that appended per-module mutation summaries to the GitHub Actions job summary, while still exporting and uploading mutation statistics as artifacts. [06c50d22](https://github.com/electrocucaracha/ai-changelog/commit/06c50d22357835a3f339056651e82e44b32c9dc5)

## [6.1.4] - 2026-08-10

### Fixed

- Resolved issues with variable expansion in Bash by assigning the GitHub Actions expression for functional test outcome to an environment variable, ensuring correct evaluation and improving script reliability. [d14eeee3](https://github.com/electrocucaracha/ai-changelog/commit/d14eeee3b9154d84397f73e48f1574cd11b051ac)

## [6.1.3] - 2026-08-10

### Fixed

- The CI workflow now correctly sets proxy environment variables for test tools by propagating lowercase variants from their uppercase counterparts, resolving inconsistent network behavior and preventing unnecessary job failures. [79bc8616](https://github.com/electrocucaracha/ai-changelog/commit/79bc86161f98fce3db97b2bbea7921166fb09b31)

## [6.1.2] - 2026-08-10

### Fixed

- Stabilized functional tests to reliably run in any runner environment by explicitly setting NO_PROXY and related variables for localhost and disabling proxy variables during test execution. [6b517c28](https://github.com/electrocucaracha/ai-changelog/commit/6b517c28a86e6e60c711b125b2e479dca05cfa3b)

## [6.1.1] - 2026-08-10

### Changed

- Optimized functional test reliability by ensuring all diagnostics and logs are collected even on failure and by bypassing proxies to improve debuggability of test failures. [9b9cc194](https://github.com/electrocucaracha/ai-changelog/commit/9b9cc194a3f5465e2c73706b7725f667b49a49c8)

## [6.1.0] - 2026-08-10

### Added

- Enhanced functional test diagnostics and summary output to accelerate root-cause analysis for CI failures by collecting additional diagnostics, extracting failed test cases, and providing troubleshooting hints. [299cb04e](https://github.com/electrocucaracha/ai-changelog/commit/299cb04ebc7de5fff5bdf4022a8280ed05fdcc16)

## [6.0.1] - 2026-08-10

### Changed

- Upgraded several dependencies to their latest versions, removed the sentry-sdk dependency, and introduced pydantic-settings as a new dependency for litellm, ensuring the environment stays current and reducing potential dependency conflicts. [244cc39e](https://github.com/electrocucaracha/ai-changelog/commit/244cc39ef0a50d3665612187592f02f9b6044295)

## [6.0.0] - 2026-08-10

### Removed

- Simplified the workflow by updating the upload-artifact and download-artifact actions to newer versions and removing redundant environment variables. [9d255ada](https://github.com/electrocucaracha/ai-changelog/commit/9d255ada79386979531edf0d88e1e784083598cb)

## [5.9.1] - 2026-08-10

### Changed

- Improved CI transparency and maintainability by publishing a Markdown summary of functional test results and token usage, reducing external dependencies, and explicitly surfacing test exit codes. [08de597c](https://github.com/electrocucaracha/ai-changelog/commit/08de597c00724491e32fa59dc5341bb4a97e11bf)

## [5.9.0] - 2026-08-10

### Added

- Enabled users to monitor and optimize LLM resource consumption by tracking aggregate token usage for completions. [66e6e475](https://github.com/electrocucaracha/ai-changelog/commit/66e6e4758e066c09396329b4e1ad3b4da28a3808)

## [5.8.0] - 2026-08-10

### Added

- Enabled new integration testing capabilities to ensure compatibility with external LLM providers by running functional tests against a live LLMock server and validating CLI behavior with the mock endpoint. [51ee29d9](https://github.com/electrocucaracha/ai-changelog/commit/51ee29d9fe4bf9cf1a0baedde4d645fc423fd6ef)

## [5.7.0] - 2026-08-10

### Added

- Enabled robust error handling and edge case coverage across core modules by introducing comprehensive tests for invalid input, unreachable APIs, and unexpected commit data. [a6b61abd](https://github.com/electrocucaracha/ai-changelog/commit/a6b61abdd94e4979df30fc6bf3cac39eac30b7b3)

## [5.6.0] - 2026-08-10

### Added

- Enabled the test for commit diff logs to verify that error handling logs all expected messages by asserting the presence of a "bad diff" warning in addition to the existing warning for failing to retrieve a diff. [1489c437](https://github.com/electrocucaracha/ai-changelog/commit/1489c43754486f70fd931747e83d1cbe39f4e0b1)

## [5.5.0] - 2026-08-10

### Added

- Enforced minimum code coverage and mutation testing thresholds, defaulting to 95% for each, to improve visibility and accountability for test quality and prevent accidental drops in coverage or mutation score. [6c4f61b1](https://github.com/electrocucaracha/ai-changelog/commit/6c4f61b1ce7d6e96241d03db1f80d164b4e7a6c1)

## [5.4.1] - 2026-08-09

### Changed

- Stabilized the git_helper test by enforcing exact log message matching for missing notes namespace, preventing false positives from unrelated messages. [2c5f92dd](https://github.com/electrocucaracha/ai-changelog/commit/2c5f92dda000349d33590c93cd360233fd383e1a)

## [5.4.0] - 2026-08-09

### Added

- Enabled debug mode for mutation testing, providing more detailed output that aids in troubleshooting and refining the testing process. [439bc3b6](https://github.com/electrocucaracha/ai-changelog/commit/439bc3b6ed63c46180ca23e98150dbb983d81552)

## [5.3.3] - 2026-08-09

### Changed

- Simplified the "Unreleased" heading check to directly compare the stripped and lowercased heading string, improving readability and performance without altering behavior. [bd458e75](https://github.com/electrocucaracha/ai-changelog/commit/bd458e75583829440ed8fb66093378d6462dca65)

## [5.3.2] - 2026-08-09

### Changed

- Optimized mutation testing by clarifying intent with `# pragma: no mutate` comments on lines where mutations would be meaningless or noisy, and stabilized the test suite by eliminating unnecessary delays in the API failure test and verifying correct logger behavior for missing namespaces. [10741a23](https://github.com/electrocucaracha/ai-changelog/commit/10741a23babf95d59afa21237d86536a9ad3c94f)

## [5.3.1] - 2026-08-09

### Changed

- Enabled robust testing of ChangelogBuilder mutations, ensuring accurate handling of verb casing, adherence notes, and argument passing, as well as correct merged section counts in all scenarios. [47c44dc3](https://github.com/electrocucaracha/ai-changelog/commit/47c44dc39ce9ca7a37a786e25d3b89d9a3fe68e4)

## [5.3.0] - 2026-08-08

### Added

- Enabled quick insights into project activity and codebase metrics by introducing visitor and code statistics badges to the readme. [bdd98e8c](https://github.com/electrocucaracha/ai-changelog/commit/bdd98e8c30f52d9157242d096ba95b30ddeddc3a)

## [5.2.2] - 2026-08-08

### Changed

- Improved tool compatibility and clarity by consistently applying the pragma: no mutate directive to argument lines. [3d8ececd](https://github.com/electrocucaracha/ai-changelog/commit/3d8ececdcbb802780df2d896cacaf0bda5e44718)

## [5.2.1] - 2026-08-08

### Changed

- Enhanced test coverage for changelog, AI provider, and Git helper edge cases, enabling more robust regression detection and clearer expected behaviors for rare conditions. [a4f988c4](https://github.com/electrocucaracha/ai-changelog/commit/a4f988c43eeebe19232ebe81192910ec80d03eb1)

## [5.2.0] - 2026-08-08

### Added

- Enabled logging for key events such as API retries, Ollama model pulls, and fallback to note text when AI generation fails, improving traceability and debuggability for users and maintainers. [b616f111](https://github.com/electrocucaracha/ai-changelog/commit/b616f11170f763de5a62d02a1e944cc1a8b92256)

## [5.1.9] - 2026-08-08

### Changed

- Enabled direct invocation of check_mutation_gate.py and restrict_mutations.py scripts in CI environments without requiring an explicit Python interpreter. [14e4400e](https://github.com/electrocucaracha/ai-changelog/commit/14e4400e59ac7eb2a543ed2cd9dba674704565a1)

## [5.1.8] - 2026-08-08

### Changed

- Simplified the parsing of configuration values by extracting and centralizing related logic into standalone functions, improving testability and reducing code duplication without altering functional behavior. [c5776bfa](https://github.com/electrocucaracha/ai-changelog/commit/c5776bfad105134d9371789cc3d3cf7e420aee8a)

## [5.1.7] - 2026-08-08

### Fixed

- Resolved error handling for parse_int_stat by raising clear ValueErrors for unsupported input types. [edf236dc](https://github.com/electrocucaracha/ai-changelog/commit/edf236dce97dc2f7ba6bcae28cb8c8b4bdb033ef)

## [5.1.6] - 2026-08-08

### Changed

- Enabled static type checking in the test suite by including mypy and its dependencies, updating Python resolution markers to support newer versions, and enhancing code quality. [36b004fb](https://github.com/electrocucaracha/ai-changelog/commit/36b004fbf5a901597564cdb927b4b53834f1117d)

## [5.1.5] - 2026-08-08

### Changed

- Enhanced the reliability of mutation testing and critical changelog and commit analysis logic by introducing a comprehensive suite of regression tests that verify correct handling of breaking changes, diff line counting, changelog rendering, semantic versioning, and logging configuration. [e489d91d](https://github.com/electrocucaracha/ai-changelog/commit/e489d91d7ae38202d9c2b1cb09437df54d0ab8dc)

## [5.1.4] - 2026-08-08

### Changed

- Simplified the CI workflow by moving mutation restriction and gate logic to standalone scripts, improving maintainability, error reporting, and reproducibility of the mutation test process without introducing any breaking changes. [bb05e670](https://github.com/electrocucaracha/ai-changelog/commit/bb05e670665cbd285030e9203c3465edc94e772d)

## [5.1.3] - 2026-08-07

### Changed

- Improved configuration parsing and validation logic to correctly prioritize environment variables and resolve 'auto' model values to platform-specific defaults. [806d3c72](https://github.com/electrocucaracha/ai-changelog/commit/806d3c72d9e68c355a1a4e49b350e0693f5336a1)

## [5.1.2] - 2026-08-07

### Changed

- Strengthened validation for Config parameters now raises ValueError for empty strings and zero values, improving code robustness and test coverage. [58f573e2](https://github.com/electrocucaracha/ai-changelog/commit/58f573e26ef1e90e2a6df9b7139c3eb8931aca11)

## [5.1.1] - 2026-08-07

### Fixed

- Robustly restricts mutmut to target only the current module in the test matrix, preventing silent misconfiguration and improving maintainability. [98d92dd8](https://github.com/electrocucaracha/ai-changelog/commit/98d92dd84e9f8ef11af15736db6b77321c110cc9)

## [5.1.0] - 2026-08-07

### Added

- Enabled detailed changelog entries for versions 4.15.0 through 5.0.0, including new features, optimizations, and documentation improvements, thus enhancing project transparency and facilitating users' tracking of changes across recent releases. [5a49627f](https://github.com/electrocucaracha/ai-changelog/commit/5a49627f08895f25110849b4432e965626c4ceca)

## [5.0.0] - 2026-08-07

### Removed

- Enabled real-time progress output in CI logs for mutation testing, improving visibility into long-running test jobs. [50862f9e](https://github.com/electrocucaracha/ai-changelog/commit/50862f9e0456070e905508dc06a1e2bc64844d5b)

## [4.15.8] - 2026-08-07

### Changed

- Optimized the display of the helper function name in the changelog to avoid confusion caused by Markdown rendering issues. [729f14dc](https://github.com/electrocucaracha/ai-changelog/commit/729f14dce3259e9e3276807a2b66654517fd66ee)

## [4.15.7] - 2026-08-07

### Changed

- Enabled parallelized mutation testing by module, reducing CI duration and improving issue traceability through a single enforcement point for surviving or suspicious mutations. [2c4f2cbe](https://github.com/electrocucaracha/ai-changelog/commit/2c4f2cbe106fbe40eadcb4ba6391a3e9e795d379)

## [4.15.6] - 2026-08-07

### Changed

- Improved robustness against subtle regressions by introducing comprehensive regression tests for edge cases and surviving mutations in the main, ai_provider, changelog, and git_helper modules. [cd36538d](https://github.com/electrocucaracha/ai-changelog/commit/cd36538ddee9e38e369335530a085d599871d109)

## [4.15.5] - 2026-08-07

### Changed

- Clarified and streamlined the setup instructions for Ollama, the default provider, to improve model selection per platform, verification steps, and Git notes configuration, and simplified the bootstrap and update scenarios. [25738ddf](https://github.com/electrocucaracha/ai-changelog/commit/25738ddf60260ee4eac6fd14ea42807855e4e822)

## [4.15.4] - 2026-08-07

### Changed

- clarified the CLI reference documentation to present options in a structured table format, improving discoverability and reducing onboarding friction for new users, and grouped provider-specific variables and usage examples for enhanced readability. [f1ce5b71](https://github.com/electrocucaracha/ai-changelog/commit/f1ce5b711109315c92094f1c1abdf41ee8e4d3b8)

## [4.15.3] - 2026-08-07

### Changed

- Clarified the AI Changelog Generator's architecture and CLI behavior by introducing a detailed visual pipeline diagram and explicit explanations of each stage, enhancing onboarding for new users and maintainers. [5b68d503](https://github.com/electrocucaracha/ai-changelog/commit/5b68d503fac0e64c02eee569d63aed1648dc27bc)

## [4.15.2] - 2026-08-07

### Changed

- Clarified the file structure by relocating markdownlint disable comments below the changelog introduction, ensuring the introduction remains visible to readers without affecting the content or behavior of the changelog. [9e8d3d1a](https://github.com/electrocucaracha/ai-changelog/commit/9e8d3d1a4b92bd0ca620021db9960677714f4763)

## [4.15.1] - 2026-08-07

### Changed

- Optimized finalization for no-op runs to skip unnecessary computation and I/O, significantly improving performance for large repositories with many commits. [3f58dbbd](https://github.com/electrocucaracha/ai-changelog/commit/3f58dbbd0c341e8f62dad517df372ffd1fad7105)

## [4.15.0] - 2026-08-07

### Added

- Enabled detailed changelog entries for versions 4.14.0 through 4.14.6, improving project transparency and aligning documentation with established standards without introducing any breaking changes or requiring migration steps. [1f89b12e](https://github.com/electrocucaracha/ai-changelog/commit/1f89b12e634015e066236bc64bda14d1e6cb4e15)

## [4.14.6] - 2026-08-07

### Fixed

- Resolved the issue of brittle mutmut stats parsing by reading the stats directly from the JSON file generated by mutmut, improving reliability and maintainability, and providing clearer error messages when mutation testing fails. [24845d8f](https://github.com/electrocucaracha/ai-changelog/commit/24845d8f48c5bf5cce7bc9f6496aa86adc5b21ae)

## [4.14.5] - 2026-08-07

### Changed

- Upgraded dependencies to newer versions, ensuring the project now leverages the latest features and security patches without introducing any breaking behavior or API changes. [db959cfb](https://github.com/electrocucaracha/ai-changelog/commit/db959cfb0921244f864ac8231d04b38e5626575d)

## [4.14.4] - 2026-08-07

### Changed

- Streamlined CI runs and reduced maintenance burden by limiting the tox configuration to only include Python 3.12 in the envlist, and ensured type checking accuracy by updating the mypy configuration to target Python 3.12 and clarifying missing import overrides for supported modules. [f9564666](https://github.com/electrocucaracha/ai-changelog/commit/f9564666aa4b3b1cd50a905f4fac6530553a3d12)

## [4.14.3] - 2026-08-07

### Changed

- Streamlined the version filtering logic in the release section merge, eliminating redundant parsing of semantic versions and improving maintainability without affecting functional behavior. [aa31bf2d](https://github.com/electrocucaracha/ai-changelog/commit/aa31bf2dcc32f18eb86c174ae3f8510dad5a02c9)

## [4.14.2] - 2026-08-07

### Changed

- Updated the pre-commit hook for AI-generated commit messages to track official releases, ensuring compatibility with the latest features and bugfixes, and improving maintainability without requiring configuration changes. [9793dff1](https://github.com/electrocucaracha/ai-changelog/commit/9793dff11124e4063210ff23e60e9789bc659261)

## [4.14.1] - 2026-08-07

### Changed

- Standardized GitHub link capitalization for improved professionalism and clarity. [c1eaaeac](https://github.com/electrocucaracha/ai-changelog/commit/c1eaaeacee7c276d6feaea6923b88beb6b98693f)

## [4.14.0] - 2026-08-06

### Added

- Enabled a comprehensive CHANGELOG.md following Keep a Changelog and Semantic Versioning standards, providing a single source of truth for users and contributors to track project evolution and releases. [930f66c1](https://github.com/electrocucaracha/ai-changelog/commit/930f66c1c2655c9e4f46240d29df1aed95716305)

## [4.13.0] - 2026-08-06

### Added

- Enabled flexibility in documentation authoring by relaxing markdownlint rules for H1 headings and line length, allowing for self-contained documents and accommodating existing content without introducing breaking behavior or migration requirements. [06db21b1](https://github.com/electrocucaracha/ai-changelog/commit/06db21b1faf31764ea3888ec736c9869c4f4948c)

## [4.12.2] - 2026-08-06

### Changed

- Enabled the markdownlint-cli Node.js tool to ensure compatibility with current markdownlint rules and improve cross-platform support, requiring developers to have Node.js installed. [2374bce8](https://github.com/electrocucaracha/ai-changelog/commit/2374bce83998ab74c70e78fded5faec399379c4c)

## [4.12.1] - 2026-08-06

### Changed

- BREAKING: Stabilized changelog merging to strictly append newer release sections, preserving existing content and preventing accidental backfilling or overwriting of existing releases. [2a5ad9a4](https://github.com/electrocucaracha/ai-changelog/commit/2a5ad9a406abdb5813e3eb5edc6a55a06ecc5c1a)

## [4.12.0] - 2026-08-06

### Added

- Enabled continuous integration for unit and mutation testing on push and pull requests, preventing undetected regressions and requiring strong test coverage. [bc22d2c7](https://github.com/electrocucaracha/ai-changelog/commit/bc22d2c7c6f409c030fb1f2c9c4111a2afda7c07)

## [4.11.5] - 2026-08-06

### Changed

- Modernized the documentation structure into intent-based sections, including tutorials, how-to guides, references, and explanations, to improve discoverability and support both new and advanced users. [424f68eb](https://github.com/electrocucaracha/ai-changelog/commit/424f68ebd409674a47902f5c5a14c3a05bae802f)

## [4.11.4] - 2026-08-05

### Changed

- Updated the project's dependencies to the latest aiohttp version 3.14.3. [224bb3e3](https://github.com/electrocucaracha/ai-changelog/commit/224bb3e3b38277a3e5704c19383e697e6dd3b901)

## [4.11.3] - 2026-08-05

### Changed

- Stabilized the summary generation test by explicitly casting the mock provider to AIProvider, ensuring type safety and improving test reliability and maintainability. [80253e8e](https://github.com/electrocucaracha/ai-changelog/commit/80253e8e779e8e831c7f33d9fa1b6a999d8d263a)

## [4.11.2] - 2026-08-05

### Changed

- Capitalized "Git" in release documentation to improve consistency and professionalism, with no impact on functionality. [8cc3063e](https://github.com/electrocucaracha/ai-changelog/commit/8cc3063ee9ece26dbf83d759221358d3ad47ef0b)

## [4.11.1] - 2026-08-05

### Changed

- Normalized the .gitignore file to exclude unnecessary node_modules and package files, preventing accidental commits and keeping the repository clean and focused on source code. [c959cc5c](https://github.com/electrocucaracha/ai-changelog/commit/c959cc5ca0cb6de0d8067dc5022fdc98fce346e6)

## [4.11.0] - 2026-08-05

### Added

- Enabled reproducible, auditable release flows directly from the repository UI, reducing manual steps and errors, through the introduction of a new guide detailing how to automate releases with AI Changelog Generator in GitHub Actions. [338abb91](https://github.com/electrocucaracha/ai-changelog/commit/338abb91c0329118fcdbb093577ac2abb1ca8437)

## [4.10.1] - 2026-08-05

### Changed

- Simplified CLI test setup by introducing reusable helpers that reduce duplication and improve maintainability, allowing test logic to focus on behavior rather than scaffolding, without affecting the CLI's functionality or output. [5c1c5abb](https://github.com/electrocucaracha/ai-changelog/commit/5c1c5abb6fd10770c40b981c7a1d7c6cf0208883)

## [4.10.0] - 2026-08-05

### Added

- Enabled overall progress tracking for large repositories, allowing users to choose between 'commits' and 'work-units' modes, and introduced per-worker summary progress reporting for parallel summary generation. [1b938ad8](https://github.com/electrocucaracha/ai-changelog/commit/1b938ad808b684cf3d6c05a5765d6fd2b2168265)

## [4.9.0] - 2026-08-05

### Added

- Enabled the super-linter to correctly use the main branch for linting by setting the DEFAULT_BRANCH to "main", preventing unexpected linter configuration issues and ensuring correct branch-based linting behavior. [81caad26](https://github.com/electrocucaracha/ai-changelog/commit/81caad26a5b3eb40f8c6f6cfa735872b1ddd2c5f)

## [4.8.2] - 2026-08-05

### Changed

- Enabled support for new AI features and code formatting by introducing headroom-ai 0.34.0 and toon-format 0.9.0b1 as dependencies, and also updated posthog to 7.38.0 for improved analytics integration. [aba090dd](https://github.com/electrocucaracha/ai-changelog/commit/aba090dda8b4470c21d5d5432747c92051a7081a)

## [4.8.1] - 2026-08-05

### Changed

- Upgraded markdownlint and ai-prepare-commit-msg hook versions to the latest, bringing bugfixes and new features for improved linting accuracy and compatibility. [1ca52dc2](https://github.com/electrocucaracha/ai-changelog/commit/1ca52dc245fa8b3c159a21c681a159576bf9c42b)

## [4.8.0] - 2026-08-05

### Added

- Enabled AI integration and code formatting capabilities by incorporating headroom-ai and toon-format into the project's dependencies, supporting upcoming features with no expected compatibility issues but requiring downstream consumers to ensure these packages do not conflict with their environments. [d0cb28e1](https://github.com/electrocucaracha/ai-changelog/commit/d0cb28e1b8331548407d55d3915f68c49dc224bd)

## [4.7.0] - 2026-08-05

### Added

- Enabled robust retry logic with exponential backoff, automatic Ollama model pulling, and sanitized model output to ensure reliable and clean changelog entries. [5665e5a0](https://github.com/electrocucaracha/ai-changelog/commit/5665e5a0fdf9a4cd93b195f22b1a340320de1461)

## [4.6.0] - 2026-08-05

### Added

- Enabled downstream tools to consume repository state in both structured and TOON formats, improving integration and automation capabilities. [1997dbeb](https://github.com/electrocucaracha/ai-changelog/commit/1997dbeb0f863f841b657cc9b14c72debb8001d0)

## [4.5.0] - 2026-08-05

### Added

- BREAKING: Improved changelog merging now replaces changed or removed release sections instead of appending them, ensuring idempotency and correcting stale entries in place, and existing changelog behavior is updated on rerun. [75e5a7e2](https://github.com/electrocucaracha/ai-changelog/commit/75e5a7e2f42bd38456dbcc577ba80626e30e0642)

## [4.4.0] - 2026-08-05

### Added

- BREAKING: Determined at runtime, the default model now adapts to Apple Silicon Macs, resolving to the quantized Llama 3.1 8B Instruct variant for improved latency and quality, while other systems continue to use the standard Llama 3.1 model. [5acacf28](https://github.com/electrocucaracha/ai-changelog/commit/5acacf28ec70b519bcf126c67a6f3dfc4b578431)

## [4.3.0] - 2026-08-05

### Added

- Enabled changelog entries to diversify repeated leading power verbs per category, improving readability for large releases. [668f5bf1](https://github.com/electrocucaracha/ai-changelog/commit/668f5bf172468c3b042dee0610b84cdd544131e9)

## [4.2.2] - 2026-08-05

### Changed

- Simplified the readme to direct users to the GitHub Pages documentation for quickstart, CLI, and provider setup details, and updated the CLI reference with new options for worker threads, retry attempts, and backoff configuration to improve discoverability of advanced CLI options and reduce onboarding friction for new users. [dc758ca7](https://github.com/electrocucaracha/ai-changelog/commit/dc758ca760663232aeadb98f82bf0479a7be9de6)

## [4.2.1] - 2026-08-05

### Changed

- Updated the pre-commit hook configuration to point to the official GitHub mirror of the bashate repository, ensuring better availability and alignment with current openstack project hosting. [e6da183f](https://github.com/electrocucaracha/ai-changelog/commit/e6da183f0a1560f0564f2d1c70563b91e7ad24b6)

## [4.2.0] - 2026-08-04

### Added

- Extracted PR author and approver identities from commit messages to support GitHub merge and trailer formats, improving traceability and enabling release notes to reflect reviewer context when available. [e561d84d](https://github.com/electrocucaracha/ai-changelog/commit/e561d84d237591a7ffc29bbf6979fe0041406104)

## [4.1.10] - 2026-08-04

### Changed

- Resolved the issue of insufficient permissions for workflow operations by switching to WORKFLOW_TOKEN, ensuring the workflow completes successfully without breaking behavior. [378da27f](https://github.com/electrocucaracha/ai-changelog/commit/378da27f235aac10571b09840b52aa888d69c40d)

## [4.1.9] - 2026-08-04

### Changed

- Updated project dependencies to use Python 3.12 as the minimum required version, affecting dependencies such as aiohttp which was updated to version 3.14.3. [a7afcc78](https://github.com/electrocucaracha/ai-changelog/commit/a7afcc78c52e776f3ae150bb3e42c8143fb16e55)

## [4.1.8] - 2026-08-04

### Changed

- Updated the pre-commit hook to use the latest revision, ensuring compatibility with new features and benefiting from upstream maintenance. [39ea9ae2](https://github.com/electrocucaracha/ai-changelog/commit/39ea9ae27b09702cd16f6cf952eae9239ac8c02f)

## [4.1.7] - 2026-08-04

### Changed

- Optimized the scheduled dependency update workflow to prevent overlapping runs and ensure secure repository access by removing the default GitHub token fallback and introducing explicit step names for improved Actions UI readability. [08a0d73d](https://github.com/electrocucaracha/ai-changelog/commit/08a0d73dd566f328b6abbc66a5d7ac642c3d7207)

## [4.1.6] - 2026-08-04

### Changed

- Simplified argument lists in test assertions by splitting long lists across multiple lines and indenting them consistently, aligning with standard Python formatting practices without introducing functional changes. [ddc35dc8](https://github.com/electrocucaracha/ai-changelog/commit/ddc35dc85744805c62d884361a5cf67075be7826)

## [4.1.5] - 2026-08-04

### Changed

- Stabilized build reproducibility and security by explicitly setting minimum versions for key dependencies and enforcing versions with known CVE fixes through added [tool.uv] constraints. [e9e1b9b8](https://github.com/electrocucaracha/ai-changelog/commit/e9e1b9b8f2c9cc1ccc4c7816536274f4e549773f)

## [4.1.4] - 2026-08-04

### Changed

- BREAKING: Simplified configuration by transitioning to provider-native environment variables for key and base URL management, eliminating reliance on legacy gateway variables. [010dca92](https://github.com/electrocucaracha/ai-changelog/commit/010dca92bbfc5f97c9ff6b0270e7c79f433cc515)

## [4.1.3] - 2026-08-04

### Changed

- Modernized the AI-generated changelog prompt to use strong action verbs that more accurately convey the intent and impact of changes for technical users. [ed0bfc4d](https://github.com/electrocucaracha/ai-changelog/commit/ed0bfc4d1f8b2d4e9bb68afc539af9e94404dca7)

## [4.1.2] - 2026-08-04

### Changed

- Simplified the GitHub Action commit hash resolution logic to reduce code duplication and improve maintainability, with no impact on the update process. [14f7fa77](https://github.com/electrocucaracha/ai-changelog/commit/14f7fa774a08115976f5402c5b2cb16b27c317ea)

## [4.1.1] - 2026-08-04

### Changed

- Stabilized CI run reliability by updating action dependencies to the latest patch versions, ensuring compatibility and stability with upstream changes. [35cd2ced](https://github.com/electrocucaracha/ai-changelog/commit/35cd2cedc712dc705bae55e7c4988843ded19607)

## [4.1.0] - 2026-08-04

### Added

- Enabled consistent YAML style checks by enforcing a project-specific configuration with relaxed rules that accommodate common patterns in configuration files. [b102bd8d](https://github.com/electrocucaracha/ai-changelog/commit/b102bd8d5f3a683d40c8af2b7c888de05559f3e0)

## [4.0.5] - 2026-08-04

### Changed

- Clarified and standardized the format of generated release notes to improve their clarity and consistency for users and maintainers. [90cce791](https://github.com/electrocucaracha/ai-changelog/commit/90cce791d1582e6a2403b17b944bfcf8925dd688)

## [4.0.4] - 2026-08-04

### Fixed

- The GitHub Actions CI script now consistently selects the latest annotated tag when both annotated and lightweight tags exist for the same version. [1aceb97c](https://github.com/electrocucaracha/ai-changelog/commit/1aceb97cbcebc6eeedb3de0c71b7c346c5dfd625)

## [4.0.3] - 2026-08-04

### Changed

- Simplified subprocess call recording in tests to reduce repetition and potential inconsistencies, improving test maintainability and clarity. [3a9062b6](https://github.com/electrocucaracha/ai-changelog/commit/3a9062b6a359d2daf3105ee343a55c835c7bb098)

## [4.0.2] - 2026-08-04

### Fixed

- Resolved super-linter YAML loading issues and ensured successful AI-inference checks by renaming the YAML configuration file, installing the Copilot CLI, switching to a compatible AI model, and configuring environment variables. [2fa255a0](https://github.com/electrocucaracha/ai-changelog/commit/2fa255a01aa37b5c61958e0864f9ace212d4e45f)

## [4.0.1] - 2026-08-04

### Changed

- Simplified the usage of timezone-aware datetimes in tests to align with Python 3.11+ best practices, removing the need for timezone imports without affecting functional behavior. [d20558db](https://github.com/electrocucaracha/ai-changelog/commit/d20558dbc3547c8ff18d40bb4f07ed80ffc629e4)

## [4.0.0] - 2026-08-04

### Removed

- BREAKING: Hardened the project's Python compatibility by raising the minimum required version to 3.12 and dropping support for earlier versions, ensuring the project stays current with Python releases and reducing the risk of dependency conflicts. [7fddcf8f](https://github.com/electrocucaracha/ai-changelog/commit/7fddcf8f2df14a009c9f8464c7ec72f72490868e)

## [3.0.4] - 2026-08-04

### Changed

- Normalized action version comments in GitHub Actions workflows to consistently use the "v" prefix, aligning with the tag format used by most upstream projects, without introducing any functional changes to action pinning or workflow execution. [d8042975](https://github.com/electrocucaracha/ai-changelog/commit/d80429754afd450b78dff84b7066e2222f23679d)

## [3.0.3] - 2026-08-04

### Changed

- Upgraded dependencies to the latest versions, including posthog to 7.37.3 for recent bugfixes and improvements, gitpython to 3.1.58 for better compatibility and stability, hf-xet to 1.6.0 to ensure support for the latest features, and adjusted exceptiongroup's typing-extensions marker for Python 3.13 compatibility. [cd71b626](https://github.com/electrocucaracha/ai-changelog/commit/cd71b6260fe5ac6a249ad3a3c7703c407ff1f9ee)

## [3.0.2] - 2026-08-04

### Changed

- Optimized documentation style for clarity and consistency by correcting typos and standardizing terminology. [48e8f147](https://github.com/electrocucaracha/ai-changelog/commit/48e8f147c3b2380089093ebc656cfd0849bc9009)

## [3.0.1] - 2026-08-04

### Changed

- Stabilized the rendering of Markdown instructions and agent configuration by enforcing consistent YAML formatting and proper code block endings. [54cdcd4f](https://github.com/electrocucaracha/ai-changelog/commit/54cdcd4f1ab0fa934cd7212bfed5cf9036aba449)

## [3.0.0] - 2026-08-04

### Removed

- Simplified the project configuration by eliminating outdated telemetry data that is no longer relevant to the current setup. [25d504ff](https://github.com/electrocucaracha/ai-changelog/commit/25d504ff1bf9f230647e81a054d9a1255490c7a4)

## [2.8.1] - 2026-08-04

### Changed

- Imports are now ordered consistently according to standard Python conventions, with no functional impact expected. [2562a5be](https://github.com/electrocucaracha/ai-changelog/commit/2562a5be0314c092998320c1f4f775a1771bac44)

## [2.8.0] - 2026-08-03

### Added

- Enabled unit tests to run against a matrix of Python versions (3.10, 3.11, and 3.12), improving detection of compatibility issues and requiring downstream jobs to be updated to use the new matrix strategy. [c9543323](https://github.com/electrocucaracha/ai-changelog/commit/c9543323428941ac63440769655b22ced48c23e3)

## [2.7.0] - 2026-08-03

### Added

- Enabled initial documentation for the AI Changelog Generator, including a project overview, quickstart guide, CLI reference, and detailed explanation of the changelog generation flow, covering prerequisites, usage examples, environment variable configuration, and integration with LiteLLM and GitHub Copilot providers. [0c428e08](https://github.com/electrocucaracha/ai-changelog/commit/0c428e085322230c2161f78ccfd4901bf513844e)

## [2.6.1] - 2026-08-03

### Changed

- Streamlined the readme overview and quickstart for improved clarity and accessibility by reorganizing content, eliminating redundant sections, and providing direct installation and usage instructions. [6fef8a22](https://github.com/electrocucaracha/ai-changelog/commit/6fef8a225dc71b18ca73b40095c6630dc7779e42)

## [2.6.0] - 2026-08-03

### Added

- Enabled regular mutation testing to catch undetected bugs and increase confidence in test coverage. [9bf5991c](https://github.com/electrocucaracha/ai-changelog/commit/9bf5991cace19080fb6fdee340face1004faaeae)

## [2.5.0] - 2026-08-03

### Added

- Enabled developers to effectively manage and maintain lean, maintainable codebases by introducing a Universal Janitor agent specification outlining strategies for code elimination, simplification, dependency hygiene, test optimization, and documentation cleanup. [10dd457f](https://github.com/electrocucaracha/ai-changelog/commit/10dd457f7f906f5170b55631fe8977d5ee334ccc)

## [2.4.0] - 2026-08-03

### Added

- Enabled code quality checks and commit message assistance by introducing a .pre-commit-config.yaml file with various hooks and updating the CI script to run pre-commit autoupdate after dependency sync. [1f54dce1](https://github.com/electrocucaracha/ai-changelog/commit/1f54dce15d60afcae1e0afd6d867f425588c0811)

## [2.3.0] - 2026-08-03

### Added

- Enabled CLI configuration via environment variables for all major options, improving usability in automated environments and enabling easier configuration management without introducing any breaking changes. [7dcc678e](https://github.com/electrocucaracha/ai-changelog/commit/7dcc678e58bd63e02c2fe2987ba8e0ed635d06c9)

## [2.2.0] - 2026-08-03

### Added

- Enabled clear and consistent documentation for contributors by introducing Markdown and Python guidelines that standardize writing practices, improve maintainability, and clarify expectations for long-term project health. [de57ed4b](https://github.com/electrocucaracha/ai-changelog/commit/de57ed4bec855085fea21114ab597fbe032c0c5c)

## [2.1.2] - 2026-08-03

### Changed

- The versions of several dependencies, including aiohttp and aiohappyeyeballs, were updated to their latest versions, potentially requiring migration steps to ensure compatibility. [56e3a7a2](https://github.com/electrocucaracha/ai-changelog/commit/56e3a7a29295cdb389b8cd15658ba666ab62a57e)

## [2.1.1] - 2026-08-03

### Changed

- Upgraded GitHub Actions dependencies to their latest stable versions, ensuring compatibility with the latest runner environments and reducing the likelihood of future issues related to deprecated or insecure actions. [c94db83f](https://github.com/electrocucaracha/ai-changelog/commit/c94db83fb0e7a0928bdd91318424eb1dbffa2933)

## [2.1.0] - 2026-08-03

### Added

- Enabled display of a shell-escaped execution command at startup, masking sensitive values and providing a reproducible invocation for debugging, with the command printed after repository detection and before destructive actions, and introducing the CHANGELOG_MODEL environment variable for the --model option. [cb5357fe](https://github.com/electrocucaracha/ai-changelog/commit/cb5357fe11223689cc15987fd432ea4478f8c796)

## [2.0.0] - 2026-08-03

### Removed

- Simplified the lint process by removing the dependency on pyink, allowing it to rely solely on black, ruff, and isort for code formatting. [506deb9e](https://github.com/electrocucaracha/ai-changelog/commit/506deb9e7b0ee362767445e2096c8e42892e814c)

## [1.1.0] - 2026-08-03

### Added

- Enabled project-level autonomy over model selection by introducing internal LiteLLM gateway routing support, allowing users to route requests through an internal gateway via environment variables or CLI options for API base, key, and extra headers. [16e47d5f](https://github.com/electrocucaracha/ai-changelog/commit/16e47d5fba9f18ed072213ac6db119234c6cc892)

## [1.0.4] - 2026-04-24

### Changed

- Standardized GitHub Actions versions across lint, spell check, and update workflows, preserving repository-specific behavior, and updated API contracts accordingly. [027384f0](https://github.com/electrocucaracha/ai-changelog/commit/027384f0c1faa07e0a4065aab773d28722705192)

## [1.0.3] - 2026-04-24

### Fixed

- The GitHub workflow for updating dependencies now stabilizes its token usage by enabling a fallback to the GitHub token if the WORKFLOW_TOKEN secret is missing. [d39df302](https://github.com/electrocucaracha/ai-changelog/commit/d39df3024d775b08ddb2c30c0032102b080bbf3f)

## [1.0.2] - 2026-03-27

### Changed

- Enabled the project's chosen toolchain by configuring yamllint and isort, and disabling pylint, ensuring consistent Python formatting with ruff and black. [412ec04d](https://github.com/electrocucaracha/ai-changelog/commit/412ec04d77b1880b4c86598f3d1675c6d2da4d85)

## [1.0.1] - 2026-03-27

### Changed

- Stabilized code quality by resolving a range of linting issues and configuring a super-linter to enforce consistent formatting and best practices, with no breaking changes or migration requirements. [08caaceb](https://github.com/electrocucaracha/ai-changelog/commit/08caacebaee07c19c8cdbbe33bc4ecf00ac02b10)

## [1.0.0] - 2026-03-22

### Added

- Enabled the AI Changelog Generator tool to automate changelog creation by generating AI-powered summaries of Git commit diffs, supporting multiple AI providers and integrating with Git for consistent and up-to-date changelogs. [46dcebfa](https://github.com/electrocucaracha/ai-changelog/commit/46dcebfabc9ae917ab3cb684c98e9a16b53f4ab4)
