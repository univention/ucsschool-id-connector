## Accounting

- Univention GmbH (424)
- Development: TBD


## Story

As a \<role\><br/>
I can \<capability\>,<br/>
so that \<receive benefit\>.

## Context/description

A little context to the issue. Where does the task come from, what is needed for implementation. Everything which is important but doesn't fit the user story syntax can be written down here.

A user story should be self-contained and provide value when shipped. It should also contain a "single source of truth".

Additional points:

- If possible, list implementation constraints here (e.g. after a refinement)
- Separation to other user stories
- Desired artifacts (package, documentation, release, etc.)
- Specific requirements regarding documentation if required

## Acceptance criteria & steps for reproduction

- [ ] TODO replace me
- [ ] All changed lines are covered by a unit test, if possible.
  - [ ] Happy case.
  - [ ] Unhappy case (errors and edge cases).
- [ ] There is at least one end-to-end test that covers the changed lines.
- [ ] Evaluate performance of the change.
  - [ ] Read the parent epic and verify performance requirements.
  - [ ] If necessary, performance tests exist. See [Performance commitment](https://git.knut.univention.de/univention/internal/decision-records/-/blob/main/ucsschool/0008-performance-commitment.md)
  - [ ] If there are no specific performance requirements, improve or at least avoid worsening existing performance, if possible.
  - [ ] Document reasons for worse performance in the code and on the ticket, if applicable.

If the changes affect security features such as authentication or authorization:

- [ ] The affected security feature has a dedicated end to end integration test.

## QA

Please explicitly check off all steps performed in the QA process.
If certain steps are not applicable, please use ~strikethrough~ and node why these steps where not performed.

## Technical QA

Technical QA is focused on the code quality and basic runability of the code.
All Technical QA steps should also be performed by the implementer before handing over to QA.

- [ ] Code review on the merge request:
  - [ ] Changelogs are present.
  - [ ] Tests sufficiently cover the changed lines of code.
- [ ] Pipelines pass.
- [ ] App installation succeeds on a test VM.
- [ ] App update succeeds on a test VM.
- [ ] Basic smoke test:
  - [ ] If a service was changed (added, modified) the service is running after the installation and restarting works without problems. If it was removed, it must not be running any more.
  - [ ] The UCS@school ID Connector API is running.
  - [ ] The UCS@school ID Connector Queue Management is working.
  - [ ] Cron jobs, listeners, etc. actually run.
  - [ ] Permissions are checked for files (e.g., a script must be executable, right ownership of directories and created files in regard to data security).
- [ ] Manual test run:
  - [ ] New tests pass.

## Functional QA

Functional QA focuses on the user using the UCS@school ID Connector

- [ ] Post a QA plan on the gitlab issue of what will be tested:
  - [ ] Include a happy path and multiple non-happy path scenarios.
  - [ ] All software components that might be affected, not just the code that was changed.
  - [ ] Verify that examples in the documentation of the changed components still work.
  - [ ] Agree on QA plan with implementer.
- [ ] Manually run the QA plan:
  - [ ] Use the Swagger UI of the Kelvin API and the UCS@school Import to create test users including multi school users.
  - [ ] Check the log files for unexpected warnings or errors and if the log levels are correct regarding their information.
- [ ] Document all reproduction steps of the QA plan:
  - [ ] What commands were used to test?
  - [ ] What input values were used to test? Why were these values chosen?
  - [ ] Get creative and try to break the implementation

## Before merge

 No merge without:

- [ ] Verify again that the integration tests pass locally on your vm and pipelines pass.
- [ ] Branch tests for [ID Connector](https://jenkins2022.knut.univention.de/job/UCSschool-5.0/view/Daily%20Tests/job/UCSschool%20ID%20Connector/) pass.
- [ ] Branch tests for [ID Broker](https://jenkins2022.knut.univention.de/job/UCSschool-5.0/view/Daily%20Tests/job/ID%20Broker/) pass.

## After Merge

- [ ] Daily Jenkins tests pass after build.
- [ ] Installation succeeds on a test VM.
- [ ] Smoke test installation: see section Technical QA.
- [ ] Gitlab issue is added to release issue.


/label ~"App::ID Connector"
/label ~"Status::Unrefined"
/label ~"Team::UCS@school"
