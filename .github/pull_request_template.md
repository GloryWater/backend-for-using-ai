<!-- filepath: .github/pull_request_template.md -->

# Pull Request

## Description

<!-- Provide a clear and concise description of what this PR does -->

## Type of Change

<!-- Mark the appropriate option with an [x] -->

- [ ] 🐛 Bug fix (non-breaking change that fixes an issue)
- [ ] ✨ New feature (non-breaking change that adds functionality)
- [ ] 💥 Breaking change (fix or feature that would cause existing functionality to change)
- [ ] 📚 Documentation update
- [ ] 🧹 Code cleanup / Refactoring
- [ ] ⚡ Performance improvement
- [ ] 🧪 Test update (adding or updating tests)
- [ ] 🔧 Configuration change
- [ ] 🚨 Security fix

## Related Issues

<!-- Link any related issues using GitHub keywords (e.g., "Closes #42", "Fixes #123", "Related to #567") -->

Closes #

## Checklist

Before submitting this PR, please confirm:

- [ ] **Tests pass:** I have run all relevant tests (`uv run pytest`) and they pass successfully
- [ ] **Pre-commit passes:** I have run `uv run pre-commit run --all-files` and it passes
- [ ] **Type checking:** I have run `uv run mypy src/` and it passes (or errors are justified)
- [ ] **Code style:** My code follows the project's style guidelines (Ruff formatting)
- [ ] **Documentation updated:** I have updated README.md, docstrings, or other documentation as needed
- [ ] **Changelog updated:** I have added an entry to CHANGELOG.md (if applicable)
- [ ] **Environment variables:** I have documented any new environment variables in README.md
- [ ] **No sensitive data:** I have not committed any API keys, passwords, or secrets
- [ ] **Backward compatible:** This change is backward compatible (or I have documented migration steps)

## Testing

### How to Test

<!-- Describe how reviewers can test your changes -->

1. Step one
2. Step two
3. Step three

### Test Evidence

<!-- Paste test output, screenshots, or logs that demonstrate your changes work -->

```bash
# Example: Run specific tests
uv run pytest tests/test_your_feature.py -v
```

## Changes Summary

<!-- List the key changes in this PR -->

### Files Changed

- `src/...` — Description of changes
- `tests/...` — Description of changes
- `docs/...` — Description of changes

### New Features

<!-- Describe any new features added -->

- Feature 1
- Feature 2

### Bug Fixes

<!-- Describe any bugs fixed -->

- Fixed issue where...
- Resolved problem with...

## Screenshots (if applicable)

<!-- For UI changes, include before/after screenshots -->

| Before | After |
|--------|-------|
| ![Before](link) | ![After](link) |

## Deployment Notes

<!-- Any special considerations for deployment -->

- [ ] Requires database migration
- [ ] Requires environment variable changes
- [ ] Requires service restart
- [ ] Can be deployed independently

### Migration Steps

<!-- If this PR requires special deployment steps, describe them here -->

```bash
# Example: Run migration
uv run alembic upgrade head
```

## Performance Impact

<!-- If this PR affects performance, describe the impact -->

- [ ] No performance impact
- [ ] Performance improved (describe below)
- [ ] Performance degraded (justify why)

### Benchmarks

<!-- If applicable, include benchmark results -->

```
Before: X requests/second, P99 latency: Y ms
After:  X requests/second, P99 latency: Y ms
```

## Security Considerations

<!-- If this PR affects security, describe the impact -->

- [ ] No security impact
- [ ] Security improved (describe below)
- [ ] Security concern (must be addressed before merge)

### Security Details

<!-- Describe any security-related changes -->

---

## Additional Context

<!-- Add any other context about the PR here -->

---

## Reviewer Notes

<!-- Any specific areas you'd like reviewers to focus on -->

<!--
Thank you for your contribution! 🎉
The maintainers will review your PR and provide feedback within 2-3 business days.
-->
