## IMPORTANT

You need to re-encrypt the file **BEFORE** you commit so that it stays encrypted in the repository.
**PLEASE** do not make a PR with a decrypted version of any of these files.

## Dependencies

These files are encrypted using ansible-vault

Make sure you have Ansible installed:

On OSX: `brew install ansible`
On Linux (debian-based): `sudo apt install ansible`

## Where is the vault password for each file?

Lead developer has them and will share with you when you ask.

## Recover

`cd env_configs && ansible-vault decrypt development && cp development ../.env && git reset --hard`

## Encrypt

Example to encrypt: [Ansible docs](http://docs.ansible.com/ansible/2.4/vault.html#encrypting-unencrypted-files)

`ansible-vault encrypt development`

## Edit

Example to edit: [Ansible docs](http://docs.ansible.com/ansible/2.4/vault.html#editing-encrypted-files)

`ansible-vault edit development`

## Decrypt

Example to decrypt: [Ansible docs](http://docs.ansible.com/ansible/2.4/vault.html#decrypting-encrypted-files)

```
ansible-vault decrypt development
cp development .env
```

Each environment file has a different vault password.  Please speak to the lead developer to obtain these passwords.

