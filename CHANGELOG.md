<!-- Markdownlint-disable MD024 -->

# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

<!-- markdownlint-disable MD024 -->
<!-- markdownlint-disable MD013 -->

## [Unreleased]

## [7.4.3] - 2026-08-12

### Fixed

- The Makefile now reliably installs textlint dependencies globally during formatting by prompting for a password on systems with sudo configured if necessary. [c1516a3b](https://github.com/electrocucaracha/ai-changelog/commit/c1516a3bb212362bf51cd9669faf7bd116646930)

## [7.4.2] - 2026-08-12

### Changed

- Clarified the contribution guide setup instructions to ensure accurate step numbering and provide a clear process for new contributors. [a0affb67](https://github.com/electrocucaracha/ai-changelog/commit/a0affb67818e15206238984a2fd490d2f7b6c79d)

## [7.4.1] - 2026-08-12

### Changed

- Simplified summary generation in CLI tests by centralizing logic into a shared helper function. [c1c9ad8b](https://github.com/electrocucaracha/ai-changelog/commit/c1c9ad8b361c86366573657d02d868ec800d95b5)

## [7.4.0] - 2026-08-12

### Added

- Enabled persistent changelog entry rendering for finalization stage by precomputing and storing both detailed summaries and Keep a Changelog entries as versioned JSON payloads in each Git note. [6f46ce60](https://github.com/electrocucaracha/ai-changelog/commit/6f46ce60a60d612581c631df45fc7f91c5cc367b)

## [7.3.1] - 2026-08-12

### Fixed

- Reliably formats code by ensuring textlint and its terminology rule are installed globally before running the formatter with the --fix flag. [c44e09ad](https://github.com/electrocucaracha/ai-changelog/commit/c44e09ad6608395afc33c735eca6481f02f24f95)

## [7.3.0] - 2026-08-10

### Added

- Enabled standardized code formatting across the project by introducing biome.json configuration settings for indentation style. [97e1baa7](https://github.com/electrocucaracha/ai-changelog/commit/97e1baa7317117f94182c04870fb0811eff565d0)

## [7.2.0] - 2026-08-10

### Added

- Enabled autofixing of language issues in formatting workflow through integration with Textlint, ensuring consistent prose style and improved documentation quality across the project. [fe2ef3ce](https://github.com/electrocucaracha/ai-changelog/commit/fe2ef3ce3f65a21b4c086c164abc9c53ad04257b)

## [7.1.0] - 2026-08-10

### Added

- Enabled comprehensive changelog entries for all releases from 5.1.1 through 7.0.0, providing users with a clear history of changes, enhancements, and bugfixes across recent versions. [6b5f283c](https://github.com/electrocucaracha/ai-changelog/commit/6b5f283c314462dbe9bd449241a2c71fbb3a1bfc)

## [7.0.0] - 2026-08-10

### Removed

- Simplified the CI pipeline by eliminating non-essential reporting and reducing maintenance overhead without impacting mutation testing or artifact availability. [06c50d22](https://github.com/electrocucaracha/ai-changelog/commit/06c50d22357835a3f339056651e82e44b32c9dc5)

## [6.1.4] - 2026-08-10

### Fixed

- The GitHub Actions CI script was stabilized by using an environment variable for the functional test outcome, which improves script reliability and makes it easier to read and maintain without introducing any breaking behavior or migration requirements. [d14eeee3](https://github.com/electrocucaracha/ai-changelog/commit/d14eeee3b9154d84397f73e48f1574cd11b051ac)

## [6.1.3] - 2026-08-10

### Fixed

- Resolved inconsistent network behavior during tests by propagating uppercase proxy environment variables to their lowercase counterparts and removing the redundant `no_proxy` key, allowing test tools to correctly recognize and utilize these settings. [79bc8616](https://github.com/electrocucaracha/ai-changelog/commit/79bc86161f98fce3db97b2bbea7921166fb09b31)

## [6.1.2] - 2026-08-10

### Fixed

- Functional tests now reliably run regardless of the runner environment due to explicit NO_PROXY settings for localhost and disabled proxy variables during test execution. [6b517c28](https://github.com/electrocucaracha/ai-changelog/commit/6b517c28a86e6e60c711b125b2e479dca05cfa3b)

## [6.1.1] - 2026-08-10

### Changed

- Improved functional test reliability by enabling diagnostics and logs collection on failure, determining test outcome based on step properties, and bypassing proxies through environment variable configuration. [9b9cc194](https://github.com/electrocucaracha/ai-changelog/commit/9b9cc194a3f5465e2c73706b7725f667b49a49c8)

## [6.1.0] - 2026-08-10

### Added

- Enhanced functional test diagnostics and summary output to accelerate root-cause analysis for CI failures by collecting additional diagnostic data, displaying last 200 lines of the functional test log on failure, extracting failed test cases with troubleshooting hints based on log heuristics. [299cb04e](https://github.com/electrocucaracha/ai-changelog/commit/299cb04ebc7de5fff5bdf4022a8280ed05fdcc16)

## [6.0.1] - 2026-08-10

### Changed

- Upgraded dependencies to their latest versions for compatibility and security improvements, including deepeval, gitpython, litellm, platformdirs, posthog, setuptools, and typing-inspection, while removing sentry-sdk as a dependency due to its removal from deepeval and introducing pydantic-settings for litellm. [244cc39e](https://github.com/electrocucaracha/ai-changelog/commit/244cc39ef0a50d3665612187592f02f9b6044295)

## [6.0.0] - 2026-08-10

### Removed

- Simplified workflow configuration by removing redundant environment variables from the LLM mock test job and updating artifact actions to maintain compatibility with GitHub Actions without introducing breaking behavior or security risks. [9d255ada](https://github.com/electrocucaracha/ai-changelog/commit/9d255ada79386979531edf0d88e1e784083598cb)

## [5.9.1] - 2026-08-10

### Changed

- Simplified the CI workflow to reduce external dependencies and improve transparency by replacing the LLMock server with a local Python script that publishes a test summary and captures exit codes for easier debugging. [08de597c](https://github.com/electrocucaracha/ai-changelog/commit/08de597c00724491e32fa59dc5341bb4a97e11bf)

## [5.9.0] - 2026-08-10

### Added

- Optimized LiteLLM completions now track aggregate token usage, enabling users to monitor and optimize LLM resource consumption. [66e6e475](https://github.com/electrocucaracha/ai-changelog/commit/66e6e4758e066c09396329b4e1ad3b4da28a3808)

## [5.8.0] - 2026-08-10

### Added

- Stabilized integration testing for LLM APIs by enabling functional tests against live LLMock servers, ensuring compatibility and guarding against regressions in integration scenarios. [51ee29d9](https://github.com/electrocucaracha/ai-changelog/commit/51ee29d9fe4bf9cf1a0baedde4d645fc423fd6ef)

## [5.7.0] - 2026-08-10

### Added

- Improved robustness of error handling and edge case scenarios across core modules by introducing comprehensive tests for invalid input, unrecognized formats, unreachable APIs, malformed configuration, and unexpected commit data. [a6b61abd](https://github.com/electrocucaracha/ai-changelog/commit/a6b61abdd94e4979df30fc6bf3cac39eac30b7b3)

## [5.6.0] - 2026-08-10

### Added

- Strengthened error handling for commit diff logs by introducing an assertion to verify that warnings about bad diffs are logged in addition to failing to retrieve a diff warnings. [1489c437](https://github.com/electrocucaracha/ai-changelog/commit/1489c43754486f70fd931747e83d1cbe39f4e0b1)

## [5.5.0] - 2026-08-10

### Added

- Enforced explicit minimum code coverage and mutation testing thresholds in the CI workflow to improve visibility and accountability for test quality. [6c4f61b1](https://github.com/electrocucaracha/ai-changelog/commit/6c4f61b1ce7d6e96241d03db1f80d164b4e7a6c1)

## [5.4.1] - 2026-08-09

### Changed

- Improved the `git_helper` test to verify exact log messages instead of substrings, making it more precise and reducing potential false positives from unrelated messages. [2c5f92dd](https://github.com/electrocucaracha/ai-changelog/commit/2c5f92dda000349d33590c93cd360233fd383e1a)

## [5.4.0] - 2026-08-09

### Added

- Enabled debug mode for mutation testing, providing more detailed output that aids in troubleshooting test coverage and mutation operator behavior issues. [439bc3b6](https://github.com/electrocucaracha/ai-changelog/commit/439bc3b6ed63c46180ca23e98150dbb983d81552)

## [5.3.3] - 2026-08-09

### Changed

- Simplified the check for the "Unreleased" heading to improve readability and performance without altering behavior. [bd458e75](https://github.com/electrocucaracha/ai-changelog/commit/bd458e75583829440ed8fb66093378d6462dca65)

## [5.3.2] - 2026-08-09

### Changed

- Improved test accuracy and execution speed by clarifying mutation testing intent through `# pragma: no mutate` comments and optimizing API failure tests to eliminate unnecessary delays. [10741a23](https://github.com/electrocucaracha/ai-changelog/commit/10741a23babf95d59afa21237d86536a9ad3c94f)

## [5.3.1] - 2026-08-09

### Changed

- Improved ChangelogBuilder handling of leading verb casing, adherence notes, and argument passing to ensure accurate mutation coverage and prevent subtle regressions. [47c44dc3](https://github.com/electrocucaracha/ai-changelog/commit/47c44dc39ce9ca7a37a786e25d3b89d9a3fe68e4)

## [5.3.0] - 2026-08-08

### Added

- Enabled quick insights into project activity and codebase metrics for contributors and users by introducing visitor count and code statistics badges to the readme without any breaking behavior or migration requirements. [bdd98e8c](https://github.com/electrocucaracha/ai-changelog/commit/bdd98e8c30f52d9157242d096ba95b30ddeddc3a)

## [5.2.2] - 2026-08-08

### Changed

- Improved test coverage and maintainability by introducing additional tests for logging, error handling, and concurrency in the Git and AI providers. [3d8ececd](https://github.com/electrocucaracha/ai-changelog/commit/3d8ececdcbb802780df2d896cacaf0bda5e44718)

## [5.2.1] - 2026-08-08

### Changed

- Clarified expected behaviors for rare edge cases by introducing comprehensive test suites that cover category inference, section rendering, item construction, AI model pull logic, and Git helper operations. [a4f988c4](https://github.com/electrocucaracha/ai-changelog/commit/a4f988c43eeebe19232ebe81192910ec80d03eb1)

## [5.2.0] - 2026-08-08

### Added

- Enabled key event logging for AIProvider to improve traceability and debuggability by recording warnings and info for API retries, Ollama model pulls, and fallback to note text when AI generation fails without altering the core summarization logic or output format. [b616f111](https://github.com/electrocucaracha/ai-changelog/commit/b616f11170f763de5a62d02a1e944cc1a8b92256)

## [5.1.9] - 2026-08-08

### Changed

- Enabled scripts check_mutation_gate.py and restrict_mutations.py to run directly in CI environments without requiring an explicit Python interpreter invocation. [14e4400e](https://github.com/electrocucaracha/ai-changelog/commit/14e4400e59ac7eb2a543ed2cd9dba674704565a1)

## [5.1.8] - 2026-08-08

### Changed

- Simplified parsing logic by extracting helpers to module-level functions allowing for direct imports and improved testability without altering functional behavior. [c5776bfa](https://github.com/electrocucaracha/ai-changelog/commit/c5776bfad105134d9371789cc3d3cf7e420aee8a)

## [5.1.7] - 2026-08-08

### Fixed

- Improved error messages are now provided for unexpected types encountered in stats input, enabling developers to more easily identify and address issues. [edf236dc](https://github.com/electrocucaracha/ai-changelog/commit/edf236dce97dc2f7ba6bcae28cb8c8b4bdb033ef)

## [5.1.6] - 2026-08-08

### Changed

- Enabled static type checking in the test suite by incorporating mypy and its dependencies, along with updating Python resolution markers to support newer versions explicitly. [36b004fb](https://github.com/electrocucaracha/ai-changelog/commit/36b004fbf5a901597564cdb927b4b53834f1117d)

## [5.1.5] - 2026-08-08

### Changed

- Improved mutation testing reliability by introducing comprehensive regression tests targeting previously surviving mutations in the ai_provider, changelog, git_helper, and main modules. [e489d91d](https://github.com/electrocucaracha/ai-changelog/commit/e489d91d7ae38202d9c2b1cb09437df54d0ab8dc)

## [5.1.4] - 2026-08-08

### Changed

- Simplified the CI workflow by externalizing mutation restriction and aggregation logic into reusable scripts that improve maintainability, error reporting, and reproducibility of the mutation test process with no changes to artifact handling. [bb05e670](https://github.com/electrocucaracha/ai-changelog/commit/bb05e670665cbd285030e9203c3465edc94e772d)

## [5.1.3] - 2026-08-07

### Changed

- Improved configuration parsing and validation logic by enabling comprehensive testing of boundary conditions and error handling for key fields, ensuring correct prioritization of overrides and environment variables, and resolving platform-specific defaults for 'auto' model values at initialization and load time. [806d3c72](https://github.com/electrocucaracha/ai-changelog/commit/806d3c72d9e68c355a1a4e49b350e0693f5336a1)

## [5.1.2] - 2026-08-07

### Changed

- Strengthened validation for Config parameters now raises ValueError for empty strings and zero values, improving code robustness and test coverage. [58f573e2](https://github.com/electrocucaracha/ai-changelog/commit/58f573e26ef1e90e2a6df9b7139c3eb8931aca11)

## [5.1.1] - 2026-08-07

### Fixed

- Stabilized mutation test configuration by reliably updating the only_mutate setting under [tool.mutmut] in pyproject.toml to prevent silent misconfiguration and ensure mutmut targets only the current module in the test matrix. [98d92dd8](https://github.com/electrocucaracha/ai-changelog/commit/98d92dd84e9f8ef11af15736db6b77321c110cc9)

## [5.1.0] - 2026-08-07

### Added

- Improved project transparency and user tracking capabilities through detailed changelog entries for versions 4.15.0 to 5.0.0, documenting new features, optimizations, and documentation improvements without introducing breaking behavior or migration requirements. [5a49627f](https://github.com/electrocucaracha/ai-changelog/commit/5a49627f08895f25110849b4432e965626c4ceca)

## [5.0.0] - 2026-08-07

### Removed

- Enabled real-time feedback during mutation testing by removing the --no-progress flag from the mutmut run step in CI, thereby improving visibility into long-running test jobs and leaving other workflow steps unaffected. [50862f9e](https://github.com/electrocucaracha/ai-changelog/commit/50862f9e0456070e905508dc06a1e2bc64844d5b)

## [4.15.8] - 2026-08-07

### Changed

- Optimized the helper function name to correctly display in the changelog by escaping the underscore character. [729f14dc](https://github.com/electrocucaracha/ai-changelog/commit/729f14dce3259e9e3276807a2b66654517fd66ee)

## [4.15.7] - 2026-08-07

### Changed

- Optimized mutation testing by running each module's tests in parallel and enforcing aggregate gate stats to reduce CI duration and improve issue traceability. [2c4f2cbe](https://github.com/electrocucaracha/ai-changelog/commit/2c4f2cbe106fbe40eadcb4ba6391a3e9e795d379)

## [4.15.6] - 2026-08-07

### Changed

- Enabled robustness against subtle regressions by introducing comprehensive regression tests for edge cases and specific surviving mutations in main, ai_provider, changelog, and git_helper modules. [cd36538d](https://github.com/electrocucaracha/ai-changelog/commit/cd36538ddee9e38e369335530a085d599871d109)

## [4.15.5] - 2026-08-07

### Changed

- Streamlined quickstart documentation to provide clearer and more concise instructions for setting up Ollama as the default provider, including model selection per platform, verification steps, and Git notes configuration options. [25738ddf](https://github.com/electrocucaracha/ai-changelog/commit/25738ddf60260ee4eac6fd14ea42807855e4e822)

## [4.15.4] - 2026-08-07

### Changed

- Improved discoverability and reduced onboarding friction for new users by reorganizing the CLI reference documentation into structured tables and clear sections that group provider-specific variables and usage examples. [f1ce5b71](https://github.com/electrocucaracha/ai-changelog/commit/f1ce5b711109315c92094f1c1abdf41ee8e4d3b8)

## [4.15.3] - 2026-08-07

### Changed

- Clarified the architecture and CLI behavior of the AI Changelog Generator by significantly expanding documentation to include detailed explanations of each pipeline stage and a visual pipeline diagram, improving onboarding for new users and maintainers. [5b68d503](https://github.com/electrocucaracha/ai-changelog/commit/5b68d503fac0e64c02eee569d63aed1648dc27bc)

## [4.15.2] - 2026-08-07

### Changed

- Clarified the structure of CHANGELOG.md by relocating markdownlint disable comments below the introduction to improve visibility and maintain a clean layout without affecting API contracts or introducing security risks. [9e8d3d1a](https://github.com/electrocucaracha/ai-changelog/commit/9e8d3d1a4b92bd0ca620021db9960677714f4763)

## [4.15.1] - 2026-08-07

### Changed

- Optimized finalization for no-op runs to skip unnecessary computations and preserve deterministic output, significantly improving performance by avoiding diff hydration and AI entry generation when no notes are updated without introducing any breaking behavior or API changes. [3f58dbbd](https://github.com/electrocucaracha/ai-changelog/commit/3f58dbbd0c341e8f62dad517df372ffd1fad7105)

## [4.15.0] - 2026-08-07

### Added

- Enabled detailed changelog entries for versions 4.14.0 through 4.14.6, covering new features, fixes, and dependency updates without introducing breaking behavior or migration requirements, thereby improving project transparency and maintainability by standardizing GitHub link capitalization and aligning markdownlint configuration with the project's style. [1f89b12e](https://github.com/electrocucaracha/ai-changelog/commit/1f89b12e634015e066236bc64bda14d1e6cb4e15)

## [4.14.6] - 2026-08-07

### Fixed

- Resilience has been improved by stabilizing the workflow's mutmut stats retrieval mechanism which now directly reads from a JSON file instead of process output reducing brittleness and enhancing maintainability with explicit error handling for missing stats files. [24845d8f](https://github.com/electrocucaracha/ai-changelog/commit/24845d8f48c5bf5cce7bc9f6496aa86adc5b21ae)

## [4.14.5] - 2026-08-07

### Changed

- Updated dependencies to ensure compatibility and security by upgrading the `aiohttp` library from version 3.14.2 to 3.14.3 across multiple platforms without introducing any breaking behavior or migration requirements. [db959cfb](https://github.com/electrocucaracha/ai-changelog/commit/db959cfb0921244f864ac8231d04b38e5626575d)

## [4.14.4] - 2026-08-07

### Changed

- Streamlined CI runs and reduced maintenance burden by limiting the tox configuration to only include Python 3.12 in the envlist and updating mypy to target this version for type checking. [f9564666](https://github.com/electrocucaracha/ai-changelog/commit/f9564666aa4b3b1cd50a905f4fac6530553a3d12)

## [4.14.3] - 2026-08-07

### Changed

- Simplified version filtering logic in the release section merge to parse each version once per iteration and streamlined related conditions improving readability and maintainability without altering functional behavior. [aa31bf2d](https://github.com/electrocucaracha/ai-changelog/commit/aa31bf2dcc32f18eb86c174ae3f8510dad5a02c9)

## [4.14.2] - 2026-08-07

### Changed

- Updated the pre-commit hook for AI-generated commit messages to track official releases by switching from a specific commit hash to the latest tagged version of ai-prepare-commit-msg. [9793dff1](https://github.com/electrocucaracha/ai-changelog/commit/9793dff11124e4063210ff23e60e9789bc659261)

## [4.14.1] - 2026-08-07

### Changed

- Standardized GitHub link capitalization for improved professionalism and clarity, and aligned markdownlint configuration to project documentation style without introducing any breaking behavior or requiring migration steps from users running previous versions. [c1eaaeac](https://github.com/electrocucaracha/ai-changelog/commit/c1eaaeacee7c276d6feaea6923b88beb6b98693f)

## [4.14.0] - 2026-08-06

### Added

- Enabled project transparency and consistent communication of evolution by introducing a comprehensive CHANGELOG.md following Keep a Changelog and Semantic Versioning standards that documents all significant additions, changes, removals, and fixes across the project's history. [930f66c1](https://github.com/electrocucaracha/ai-changelog/commit/930f66c1c2655c9e4f46240d29df1aed95716305)

## [4.13.0] - 2026-08-06

### Added

- Enabled more flexibility in document authoring by allowing multiple H1 headings and relaxing line length checks to match Jekyll's front-matter provision of the main title key. [06db21b1](https://Github.com/electrocucaracha/ai-changelog/commit/06db21b1faf31764ea3888ec736c9869c4f4948c)

## [4.12.2] - 2026-08-06

### Changed

- Enabled compatibility with current markdownlint rules and improved cross-platform support by replacing the deprecated Ruby gem with the maintained markdownlint-cli Node.js tool. [2374bce8](https://Github.com/electrocucaracha/ai-changelog/commit/2374bce83998ab74c70e78fded5faec399379c4c)

## [4.12.1] - 2026-08-06

### Changed

- BREAKING: Stabilized changelog merging to prevent accidental backfilling of old tags and ensure hand-written milestone releases are preserved. [2a5ad9a4](https://Github.com/electrocucaracha/ai-changelog/commit/2a5ad9a406abdb5813e3eb5edc6a55a06ecc5c1a)

## [4.12.0] - 2026-08-06

### Added

- Enabled continuous integration for unit and mutation testing on push and pull requests via a GitHub Actions workflow that runs tox with Python 3.12 to enforce strong test coverage and prevent undetected regressions without introducing breaking behavior. [bc22d2c7](https://Github.com/electrocucaracha/ai-changelog/commit/bc22d2c7c6f409c030fb1f2c9c4111a2afda7c07)

## [4.11.5] - 2026-08-06

### Changed

- Modernized documentation structure to organize content by intent-based sections: tutorials, guides, references, and explanations, improving discoverability for both new and advanced users with a clear grouping of conceptual overviews, step-by-step guides, and detailed reference material. [424f68eb](https://Github.com/electrocucaracha/ai-changelog/commit/424f68ebd409674a47902f5c5a14c3a05bae802f)

## [4.11.4] - 2026-08-05

### Changed

- Updated dependencies to include new versions of `aiohttp` available on PyPI. [224bb3e3](https://Github.com/electrocucaracha/ai-changelog/commit/224bb3e3b38277a3e5704c19383e697e6dd3b901)

## [4.11.3] - 2026-08-05

### Changed

- Stabilized test reliability and maintainability by explicitly casting the mock provider to AIProvider in summary generation helper. [80253e8e](https://Github.com/electrocucaracha/ai-changelog/commit/80253e8e779e8e831c7f33d9fa1b6a999d8d263a)

## [4.11.2] - 2026-08-05

### Changed

- Standardized the capitalization of "Git" in release documentation to match its proper noun status improving consistency and professionalism throughout the documentation. [8cc3063e](https://Github.com/electrocucaracha/ai-changelog/commit/8cc3063ee9ece26dbf83d759221358d3ad47ef0b)

## [4.11.1] - 2026-08-05

### Changed

- Optimized repository cleanliness by excluding node_modules and package files from version control to prevent accidental commits of dependencies and lockfiles. [c959cc5c](https://Github.com/electrocucaracha/ai-changelog/commit/c959cc5ca0cb6de0d8067dc5022fdc98fce346e6)

## [4.11.0] - 2026-08-05

### Added

- Enabled users to adopt a reproducible and auditable release flow directly from the repository UI by introducing a new guide detailing how to automate releases with AI Changelog Generator in GitHub Actions. [338abb91](https://Github.com/electrocucaracha/ai-changelog/commit/338abb91c0329118fcdbb093577ac2abb1ca8437)

## [4.10.1] - 2026-08-05

### Changed

- Simplified CLI test setup by introducing reusable helper functions that ensure consistent test execution and reduce maintenance overhead without altering the CLI's functionality or output. [5c1c5abb](https://Github.com/electrocucaracha/ai-changelog/commit/5c1c5abb6fd10770c40b981c7a1d7c6cf0208883)

## [4.10.0] - 2026-08-05

### Added

- Enabled overall progress tracking for large repositories by introducing an --overall-progress-mode option and per-worker summary progress reporting when using multiple workers for AI summarization. [1b938ad8](https://Github.com/electrocucaracha/ai-changelog/commit/1b938ad808b684cf3d6c05a5765d6fd2b2168265)

## [4.9.0] - 2026-08-05

### Added

- Enabled explicit DEFAULT_BRANCH configuration to prevent linting warnings and ensure correct branch-based linting behavior by setting it to the repository's default branch "main". [81caad26](https://Github.com/electrocucaracha/ai-changelog/commit/81caad26a5b3eb40f8c6f6cfa735872b1ddd2c5f)

## [4.8.2] - 2026-08-05

### Changed

- Introduced headroom-ai 0.34.0 and toon-format 0.9.0b1 as dependencies for new AI features and code formatting, also updating posthog to 7.38.0 for improved analytics integration with no breaking behavior or migration requirements introduced. [aba090dd](https://Github.com/electrocucaracha/ai-changelog/commit/aba090dda8b4470c21d5d5432747c92051a7081a)

## [4.8.1] - 2026-08-05

### Changed

- Upgraded markdownlint and ai-prepare-commit-msg to the latest versions ensuring compatibility and improved linting accuracy without requiring configuration changes. [1ca52dc2](https://Github.com/electrocucaracha/ai-changelog/commit/1ca52dc245fa8b3c159a21c681a159576bf9c42b)

## [4.8.0] - 2026-08-05

### Added

- Enabled AI integration and code formatting capabilities by incorporating headroom-ai and toon-format into the project's dependencies, supporting upcoming features without expected compatibility issues but requiring downstream consumers to manage potential package conflicts in their environments. [d0cb28e1](https://Github.com/electrocucaracha/ai-changelog/commit/d0cb28e1b8331548407d55d3915f68c49dc224bd)

## [4.7.0] - 2026-08-05

### Added

- Optimized AIProvider to automatically retry transient API failures and pull missing Ollama models before sanitizing model output for clean changelog entries. [5665e5a0](https://Github.com/electrocucaracha/ai-changelog/commit/5665e5a0fdf9a4cd93b195f22b1a340320de1461)

## [4.6.0] - 2026-08-05

### Added

- Enabled downstream tools to consume repository state in both structured and TOON formats by providing a serializable snapshot of repository metadata through the get_repository_info method and its optional TOON encoding variant. [1997dbeb](https://Github.com/electrocucaracha/ai-changelog/commit/1997dbeb0f863f841b657cc9b14c72debb8001d0)

## [4.5.0] - 2026-08-05

### Added

- BREAKING: Hardened changelog merging behavior to ensure idempotency and correct stale entries in place by replacing existing release sections when their content changes, potentially updating previously generated sections on rerun, while enabling users to tune parallelism and retry behavior via CLI flags or environment variables. [75e5a7e2](https://Github.com/electrocucaracha/ai-changelog/commit/75e5a7e2f42bd38456dbcc577ba80626e30e0642)

## [4.4.0] - 2026-08-05

### Added

- BREAKING: Dynamically determines and switches to optimized model variants at runtime based on the system architecture, automatically selecting the quantized Llama 3.1 8B Instruct variant for Apple Silicon Macs and the standard Llama 3.1 model elsewhere; introduces retry attempts and backoff seconds configurable via environment variables to improve resilience to transient failures, with the default model field now set to "auto" that resolves to the appropriate model during initialization, and adds a new enable_headroom flag that defaults to True for optionally enabling headroom logic. [5acacf28](https://Github.com/electrocucaracha/ai-changelog/commit/5acacf28ec70b519bcf126c67a6f3dfc4b578431)

## [4.3.0] - 2026-08-05

### Added

- Diversified repeated leading power verbs in category blocks to improve readability and reduce monotony in generated changelogs for large releases. [668f5bf1](https://Github.com/electrocucaracha/ai-changelog/commit/668f5bf172468c3b042dee0610b84cdd544131e9)

## [4.2.2] - 2026-08-05

### Changed

- Streamlined documentation to reduce duplication and maintenance overhead by directing users to GitHub Pages for quickstart, CLI, and provider setup details, while also introducing new CLI options for worker threads, retry attempts, and backoff configuration. [dc758ca7](https://Github.com/electrocucaracha/ai-changelog/commit/dc758ca760663232aeadb98f82bf0479a7be9de6)

## [4.2.1] - 2026-08-05

### Changed

- Updated the pre-commit hook configuration to utilize the official GitHub mirror for bashate repository access instead of opendev.org. [e6da183f](https://Github.com/electrocucaracha/ai-changelog/commit/e6da183f0a1560f0564f2d1c70563b91e7ad24b6)

## [4.2.0] - 2026-08-04

### Added

- Enabled summarization of PR author and approver identities in release notes for improved traceability and reviewer context when available. [e561d84d](https://Github.com/electrocucaracha/ai-changelog/commit/e561d84d237591a7ffc29bbf6979fe0041406104)

## [4.1.10] - 2026-08-04

### Changed

- Optimized GitHub token usage to enable successful pull request creation and Dockerfile updates by leveraging the WORKFLOW_TOKEN with properly configured repository secrets. [378da27f](https://Github.com/electrocucaracha/ai-changelog/commit/378da27f235aac10571b09840b52aa888d69c40d)

## [4.1.9] - 2026-08-04

### Changed

- Updated Python dependencies to require version 3.12, affecting project compatibility and potentially requiring migration steps for users running older versions. [a7afcc78](https://Github.com/electrocucaracha/ai-changelog/commit/a7afcc78c52e776f3ae150bb3e42c8143fb16e55)

## [4.1.8] - 2026-08-04

### Changed

- Updated the pre-commit hook for ai-prepare-commit-msg to ensure compatibility with new features and benefit from upstream maintenance without requiring configuration changes. [39ea9ae2](https://Github.com/electrocucaracha/ai-changelog/commit/39ea9ae27b09702cd16f6cf952eae9239ac8c02f)

## [4.1.7] - 2026-08-04

### Changed

- Optimized the scheduled dependency update workflow to prevent overlapping runs and ensure secure repository access by removing default GitHub token fallbacks and introducing explicit step names for better Actions UI readability. [08a0d73d](https://Github.com/electrocucaracha/ai-changelog/commit/08a0d73dd566f328b6abbc66a5d7ac642c3d7207)

## [4.1.6] - 2026-08-04

### Changed

- Simplified argument lists in test assertions to improve readability by splitting long lists across multiple lines and indenting them consistently without introducing any functional changes. [ddc35dc8](https://Github.com/electrocucaracha/ai-changelog/commit/ddc35dc85744805c62d884361a5cf67075be7826)

## [4.1.5] - 2026-08-04

### Changed

- Stabilized build reproducibility and security by explicitly setting minimum versions for key dependencies and introducing version constraints in the [tool.uv] section to ensure compatibility and mitigate potential vulnerabilities. [e9e1b9b8](https://Github.com/electrocucaracha/ai-changelog/commit/e9e1b9b8f2c9cc1ccc4c7816536274f4e549773f)

## [4.1.4] - 2026-08-04

### Changed

- BREAKING: Simplified configuration by transitioning from legacy gateway environment variables to provider-native settings for authentication and routing. [010dca92](https://Github.com/electrocucaracha/ai-changelog/commit/010dca92bbfc5f97c9ff6b0270e7c79f433cc515)

## [4.1.3] - 2026-08-04

### Changed

- Clarified changelog generation prompts to instruct AI to begin sentences with precise action verbs that accurately convey the intent and impact of changes for technical users. [ed0bfc4d](https://Github.com/electrocucaracha/ai-changelog/commit/ed0bfc4d1f8b2d4e9bb68afc539af9e94404dca7)

## [4.1.2] - 2026-08-04

### Changed

- Simplified maintenance of GitHub Actions by extracting logic for resolving commit hashes into a reusable function that takes the action name and version pattern as arguments. [14f7fa77](https://Github.com/electrocucaracha/ai-changelog/commit/14f7fa774a08115976f5402c5b2cb16b27c317ea)

## [4.1.1] - 2026-08-04

### Changed

- Updated action dependencies to ensure compatibility and stability in CI environments by incorporating recent bugfixes and improvements from upstream changes. [35cd2ced](https://Github.com/electrocucaracha/ai-changelog/commit/35cd2cedc712dc705bae55e7c4988843ded19607)

## [4.1.0] - 2026-08-04

### Added

- Enabled YAML linting to enforce consistent style checks while accommodating common project configuration patterns by disabling the document-start and line-length rules. [b102bd8d](https://Github.com/electrocucaracha/ai-changelog/commit/b102bd8d5f3a683d40c8af2b7c888de05559f3e0)

## [4.0.5] - 2026-08-04

### Changed

- Clarified and standardized instructions for generating release notes to improve clarity and consistency of user-facing outcomes. [90cce791](https://Github.com/electrocucaracha/ai-changelog/commit/90cce791d1582e6a2403b17b944bfcf8925dd688)

## [4.0.4] - 2026-08-04

### Fixed

- The logic for selecting the latest annotated tag in GitHub Actions has been optimized to ensure consistency and prefer annotated tags when available, improving reliability and correctness of version pinning for dependencies with no impact on other CI steps. [1aceb97c](https://Github.com/electrocucaracha/ai-changelog/commit/1aceb97cbcebc6eeedb3de0c71b7c346c5dfd625)

## [4.0.3] - 2026-08-04

### Changed

- Simplified subprocess-based test creation by introducing a helper function that encapsulates the call recording pattern and returns both the call log and a stubbed \_run function, making it easier to add or update tests in the future. [3a9062b6](https://Github.com/electrocucaracha/ai-changelog/commit/3a9062b6a359d2daf3105ee343a55c835c7bb098)

## [4.0.2] - 2026-08-04

### Fixed

- Optimized linter workflow by switching to gpt-4.1 model and introducing Copilot CLI install step with necessary environment variables, resolving super-linter YAML and ai-inference failures due to breaking changes in the Copilot CLI and AI inference actions. [2fa255a0](https://Github.com/electrocucaracha/ai-changelog/commit/2fa255a01aa37b5c61958e0864f9ace212d4e45f)

## [4.0.1] - 2026-08-04

### Changed

- Updated tests to utilize datetime.UTC for timezone-aware datetimes, aligning with Python 3.11+ best practices and improving clarity and future compatibility without affecting functional behavior. [d20558db](https://Github.com/electrocucaracha/ai-changelog/commit/d20558dbc3547c8ff18d40bb4f07ed80ffc629e4)

## [4.0.0] - 2026-08-04

### Removed

- BREAKING: Hardened project dependencies by raising the minimum required Python version to 3.12 and dropping support for earlier versions, while also removing unnecessary dependency constraints to simplify maintenance. [7fddcf8f](https://Github.com/electrocucaracha/ai-changelog/commit/7fddcf8f2df14a009c9f8464c7ec72f72490868e)

## [3.0.4] - 2026-08-04

### Changed

- Standardized action version comments in GitHub workflows to consistently include the "v" prefix matching upstream project tag formats without introducing any breaking behavior or migration requirements. [d8042975](https://Github.com/electrocucaracha/ai-changelog/commit/d80429754afd450b78dff84b7066e2222f23679d)

## [3.0.3] - 2026-08-04

### Changed

- Upgraded key dependencies to their latest versions, ensuring better compatibility and stability while reducing the risk of security issues. [cd71b626](https://Github.com/electrocucaracha/ai-changelog/commit/cd71b6260fe5ac6a249ad3a3c7703c407ff1f9ee)

## [3.0.2] - 2026-08-04

### Changed

- Modernized documentation style to enhance clarity and consistency across project references by standardizing phrasing and capitalization of tool names. [48e8f147](https://Github.com/electrocucaracha/ai-changelog/commit/48e8f147c3b2380089093ebc656cfd0849bc9009)

## [3.0.1] - 2026-08-04

### Changed

- Optimized documentation rendering by enforcing YAML standards and proper Markdown formatting throughout relevant files. [54cdcd4f](https://Github.com/electrocucaracha/ai-changelog/commit/54cdcd4f1ab0fa934cd7212bfed5cf9036aba449)

## [3.0.0] - 2026-08-04

### Removed

- Eliminated outdated DeepEval telemetry data to prevent clutter and confusion about the status of DeepEval integration without introducing any functional changes or affecting API or CLI contracts. [25d504ff](https://Github.com/electrocucaracha/ai-changelog/commit/25d504ff1bf9f230647e81a054d9a1255490c7a4)

## [2.8.1] - 2026-08-04

### Changed

- Reordered imports in tests/test_Git_helper.py to align with standard Python conventions and improve readability without any functional impact on the system's behavior. [2562a5be](https://Github.com/electrocucaracha/ai-changelog/commit/2562a5be0314c092998320c1f4f775a1771bac44)

## [2.8.0] - 2026-08-03

### Added

- Enabled unit tests to run against multiple Python versions, including 3.10, 3.11, and 3.12, improving detection of compatibility issues across supported versions with no impact on downstream jobs. [c9543323](https://Github.com/electrocucaracha/ai-changelog/commit/c9543323428941ac63440769655b22ced48c23e3)

## [2.7.0] - 2026-08-03

### Added

- Enabled initial documentation for the AI Changelog Generator, providing project overview, quickstart guide, CLI reference, and changelog generation flow details to facilitate user setup and advanced configuration. [0c428e08](https://Github.com/electrocucaracha/ai-changelog/commit/0c428e085322230c2161f78ccfd4901bf513844e)

## [2.6.1] - 2026-08-03

### Changed

- Simplified the readme overview and quickstart to provide a more direct and concise introduction to the tool and its LiteLLM integration for new users. [6fef8a22](https://Github.com/electrocucaracha/ai-changelog/commit/6fef8a225dc71b18ca73b40095c6630dc7779e42)

## [2.6.0] - 2026-08-03

### Added

- Enabled regular mutation testing to catch undetected bugs and increase confidence in test coverage through integration of mutmut with automated setup and execution via the "mutation" Makefile target. [9bf5991c](https://Github.com/electrocucaracha/ai-changelog/commit/9bf5991cace19080fb6fdee340face1004faaeae)

## [2.5.0] - 2026-08-03

### Added

- Enabled automated and manual tech debt remediation efforts through the introduction of a Universal Janitor agent specification outlining strategies for aggressive code cleanup, simplification, dependency hygiene, test optimization, and documentation maintenance. [10dd457f](https://Github.com/electrocucaracha/ai-changelog/commit/10dd457f7f906f5170b55631fe8977d5ee334ccc)

## [2.4.0] - 2026-08-03

### Added

- Enabled automated code quality checks through pre-commit configuration and autoupdate to improve code consistency and reduce manual maintenance by enforcing trailing whitespace removal, YAML validation, shell script linting, Markdown linting, YAML formatting, and spell checking. [1f54dce1](https://Github.com/electrocucaracha/ai-changelog/commit/1f54dce15d60afcae1e0afd6d867f425588c0811)

## [2.3.0] - 2026-08-03

### Added

- Enabled CLI options to be configured via environment variables such as CHANGELOG_NAMESPACE and CHANGELOG_FORCE, allowing seamless integration in automated environments and CI/CD pipelines without introducing any breaking changes. [7dcc678e](https://Github.com/electrocucaracha/ai-changelog/commit/7dcc678e58bd63e02c2fe2987ba8e0ed635d06c9)

## [2.2.0] - 2026-08-03

### Added

- Clarified contributor expectations by introducing Markdown and Python guidelines that standardize formatting, structure, typing requirements, and project-specific coding conventions. [de57ed4b](https://Github.com/electrocucaracha/ai-changelog/commit/de57ed4bec855085fea21114ab597fbe032c0c5c)

## [2.1.2] - 2026-08-03

### Changed

- Updated dependencies to require Python 3.11 and above for optimal functionality. [56e3a7a2](https://Github.com/electrocucaracha/ai-changelog/commit/56e3a7a29295cdb389b8cd15658ba666ab62a57e)

## [2.1.1] - 2026-08-03

### Changed

- Optimized GitHub Actions dependencies to their latest stable versions, ensuring compatibility with the latest runner environments and reducing maintenance burden by addressing upstream bugfixes, security patches, and performance improvements across all workflows without modifying workflow logic. [c94db83f](https://Github.com/electrocucaracha/ai-changelog/commit/c94db83fb0e7a0928bdd91318424eb1dbffa2933)

## [2.1.0] - 2026-08-03

### Added

- Enabled shell-escaped display of the current CLI invocation at startup, masking sensitive values and providing users with reproducible run details, while also introducing the CHANGELOG_MODEL environment variable for specifying the AI model to use. [cb5357fe](https://Github.com/electrocucaracha/ai-changelog/commit/cb5357fe11223689cc15987fd432ea4478f8c796)

## [2.0.0] - 2026-08-03

### Removed

- Simplified maintenance and execution time by removing pyink from the lint process which now relies solely on black, ruff, and isort for code formatting with no functional changes to code formatting expected. [506deb9e](https://Github.com/electrocucaracha/ai-changelog/commit/506deb9e7b0ee362767445e2096c8e42892e814c)

## [1.1.0] - 2026-08-03

### Added

- Enabled project-level autonomy over model selection by allowing users to route requests through an internal LiteLLM gateway via configurable environment variables and CLI options for API base, key, and extra headers. [16e47d5f](https://Github.com/electrocucaracha/ai-changelog/commit/16e47d5fba9f18ed072213ac6db119234c6cc892)

## [1.0.4] - 2026-04-24

### Changed

- Synchronized GitHub Actions workflows across lint, spell check, and update processes to ensure consistent execution behavior while preserving repository-specific settings. [027384f0](https://Github.com/electrocucaracha/ai-changelog/commit/027384f0c1faa07e0a4065aab773d28722705192)

## [1.0.3] - 2026-04-24

### Fixed

- The GitHub workflow for updating dependencies now successfully executes in all environments due to the introduction of a fallback token resolving an issue where the WORKFLOW_TOKEN secret was inaccessible. [d39df302](https://Github.com/electrocucaracha/ai-changelog/commit/d39df3024d775b08ddb2c30c0032102b080bbf3f)

## [1.0.2] - 2026-03-27

### Changed

- Simplified super-linter configurations to resolve CI failures by disabling pylint/ruff-format and enabling yamllint and isort checks while removing unnecessary python-pylint validation. [412ec04d](https://Github.com/electrocucaracha/ai-changelog/commit/412ec04d77b1880b4c86598f3d1675c6d2da4d85)

## [1.0.1] - 2026-03-27

### Changed

- Stabilized super-linter CI configuration to adhere to best practices and improve code quality by renaming `.pylintrc` to `.python-lint`, adding an `isort.cfg` file, and enforcing consistent formatting. [08caaceb](https://Github.com/electrocucaracha/ai-changelog/commit/08caacebaee07c19c8cdbbe33bc4ecf00ac02b10)

## [1.0.0] - 2026-03-22

### Added

- Enabled automated changelog generation for projects by integrating AI models to analyze Git commit diffs. [46dcebfa](https://Github.com/electrocucaracha/ai-changelog/commit/46dcebfabc9ae917ab3cb684c98e9a16b53f4ab4)
