# Gforth 0.7.3 compatibility

Gforth is absent from Debian 13's official repositories. For compatibility with
0.7.3, this repository provides an optional **local source-package build** of
`0.7.3+dfsg-10`. This is Debian's patched 0.7.3 release, not a 0.7.9 snapshot.
The packaging includes modern compiler fixes. It is sourced from Debian's pool
without adding testing/unstable APT sources or using their binary libraries.

The source descriptor and both tarballs are SHA256-pinned in
`sources/gforth-0.7.3.toml`. Initial hashes were obtained from Debian over HTTPS;
the tarball hashes match the source descriptor. This is integrity pinning, not
a claim that a maintainer's OpenPGP signature was independently authenticated.
The DFSG source omits the non-free upstream manual; the runtime remains 0.7.3
with Debian patches. Test your own Forth programs as the final compatibility check.

## Build on Debian, not on the Mac

As jamesb, from the repository, preview:

```sh
./scripts/build-gforth
```

Install build dependencies **on Debian**:

```sh
sudo apt-get install --no-remove build-essential dpkg-dev debhelper libffi-dev libtool libtool-bin libltdl-dev xz-utils curl ca-certificates
```

Build as your normal user, without sudo:

```sh
./scripts/build-gforth --apply
```

The build is kept in a fresh directory under
`~/.cache/workstation-setup/gforth/`. Progress goes to `build.log`; from another
terminal you can use `tail -f` on the path printed by the command. The source is
verified before extraction or execution. The build uses Debian 13's installed
toolchain, keeps the packaging's normal tests enabled, and runs an additional
arithmetic test from extracted packages under a temporary home directory.
No system installation is performed by the builder.

On success, it prints two commands with the exact three `.deb` paths. Run the
APT simulation first and inspect the proposed dependencies, then the install
command. This installs into normal Debian locations, tracked by dpkg; it does
not use `/opt` or overwrite files outside package management. The dependency
solver uses your existing repositories, and `--no-remove` refuses removals.

Verify installation:

```sh
gforth --version
gforth -e '1 2 + . cr bye'
```

Expect Gforth 0.7.3 and `3`, then test your projects. Keep the `.deb` files,
`source-lock.toml`, `.buildinfo`, `.changes`, and `build-packages.tsv` if you need
to reproduce or audit the installation. Builds are source-pinned; identical
binaries also depend on the compiler and other build dependency versions.

## Recovery and validation limits

A failed build leaves only its cache directory and any separately installed
build dependencies. Inspect the log and fix the cause; don't skip failed tests.
A retry creates a fresh directory. Successful reruns can install the same package
version again through APT. Remove the installed runtime, if desired, with:

```sh
sudo apt-get remove gforth gforth-lib gforth-common
```

Review APT's removal proposal before accepting it. The builder makes no changes
to APT sources, networking, boot configuration, or the workstation's main phases.

Development validation is limited to portable tests and static checks on macOS;
the Debian build and its compatibility tests have **not yet run here**.

Sources: [Debian package tracker](https://tracker.debian.org/pkg/gforth),
[pinned source descriptor](https://deb.debian.org/debian/pool/main/g/gforth/gforth_0.7.3+dfsg-10.dsc),
[Gforth upstream](https://gforth.org/).
