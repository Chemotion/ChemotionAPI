# Contributing

## Rules for code that talks to the ELN

Each rule comes from a bug that reached a release candidate.

1. **Check the body, not only the status code.** The ELN reports some failures inside a success status: `201` with `{"errors": …}`, `200` with `{"error": …}`, `{"success": false}`. `Connection` raises `ChemotionRejectedError` for these on every request. Pass `allow_error_body=True` only when the method reads such a body itself and raises something more specific.

2. **Never save from listing data.** A listing carries only part of each element. Every accessor that hands out data the caller can change (`properties`, `segments`, `analyses`, `attachments`, and any element-specific attribute such as a screen's link lists) must load the full record first, with `_ensure_loaded()`. Otherwise the load that happens later overwrites the caller's change. Code that runs while parsing uses the private fields, so constructing an element makes no request.

3. **Do not rely on the order of a listing.** The ELN orders listings by last update, not by id, and another user can change that order at any moment. Find a new element by its id or label.

4. **Start new elements from the ELN's own defaults.** The templates in `chemotion_api/elements/empty_elements/` follow the web editor's `buildEmpty`. An element the client creates must be editable in the web interface like one created there.

5. **The server decides what is valid.** Check only cheap, unambiguous requirements before sending (a required field that is empty). Otherwise send the request and pass the server's message on unchanged.

6. **Guard where the server succeeds without doing anything.** The ELN keeps only the parameters a route declares and drops the rest without an error. If a property cannot be stored through the route that saves it, refuse the write or the save with a message that says where it can be stored, rather than let the change disappear.

7. **Read job notifications through `chemotion_api.notifications`.** Background jobs (exports, imports, reports) answer through notification messages whose wording the client depends on. Keep that parsing in one place, test it against real messages, and let a timeout say what did arrive.

8. **Document side effects.** If a call makes the ELN send mail or notify other users, say so in the docstring.

9. **Every fix comes with a test that fails without it.** Run the test against the unfixed code before committing.

## Checks

`just check` runs ruff, mypy and the offline tests. The integration tests need a seeded ELN; see `tests/test_config/README.md`.
