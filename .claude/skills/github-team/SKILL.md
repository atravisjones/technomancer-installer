---
name: github-team
description: Manage the company's GitHub organization for an owner. Use when the person asks to add a teammate to the company GitHub, invite someone, see who is in it or who is still invited, or update the company's shared assistant settings.
---

# The company's GitHub

The organization's name is in `.company-github` in this folder. Its private
`assistant-settings` repository holds `company.json`: the company's trade, CRM and
phone system. When a new teammate runs setup, it reads that file so their assistant
starts with the same systems.

Only an organization **owner** can add people. Check first:

```
gh api user/memberships/orgs/<org> --jq .role
```

If it is not `admin`, tell the person an owner has to do this, and stop.

## Add a teammate

1. Ask for their GitHub username. If they have none yet, the teammate runs the setup
   file: it makes one and shows them the username to send you.
2. Check the account exists: `gh api users/<username> --jq .login`
3. Say exactly what you will do ("Invite <username> to <org> as a member") and wait
   for a yes.
4. Invite: `gh api -X PUT orgs/<org>/memberships/<username> -f role=member`
   Setup signs everyone in without organization-admin rights on purpose. If GitHub
   answers 403 or "admin:org", tell the person they need to allow it once: run
   `gh auth refresh -h github.com -s admin:org` in a terminal on this computer, type
   the code it shows on the GitHub page that opens, then try the invite again.
5. Tell the person the teammate's setup accepts the invite by itself the next time
   they click "Check again" on the company GitHub step (or they can accept it at
   `https://github.com/orgs/<org>/invitation`).

Make someone an owner (`role=admin`) only when the person asks for exactly that.

## See who is in it

- Members: `gh api orgs/<org>/members --paginate --jq '.[].login'`
- Still invited: `gh api orgs/<org>/invitations --jq '.[] | .login // .email'`

## Change the shared settings

Read `company.json`, show the change, wait for a yes, then write it back with the
contents API (`gh api -X PUT repos/<org>/assistant-settings/contents/company.json`
with `message`, base64 `content` and the current `sha`). Never put a key or token in it.

## Never

- Remove a member, change roles, or delete a repository without an explicit yes for
  that exact change.
- Put any `.env` value in GitHub.
