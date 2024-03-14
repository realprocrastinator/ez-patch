# ez-patch
A simple tool for managing, collecting and applying your patches in a much more convenient way.

## Motivation

At times, I receive numerous patches from various sources, such as the upstream repository, my colleagues, or simply because I want to make some custom local changes without submitting them to the git server. 

However, as time passes, maintaining these patches can become a painful task. To address this issue, this tool that help me can collect patches from a given repository source and generate a summary of the information in a maintainable way. 

By version controlling the collected patches and the manifest file, which are essentially in ASCII format, you can continually update the patches and use them according to your needs in the future.

## Dependencies

python3 is required

## Features & Usage

As usual, you can run `python3 pm.py --help` to see all the available features and user options. Specifically, the following commands are supported:

### Collect Patches

`gen-patches`

Generates patch files and a patch manifest file for a given repository source, with an optional filter. To use this command, run `python3 pm.py gen-patches --repo-src <git-remote-name> [--filter "<git-log-filter-name1>:<pattern>;<git-log-filter-name2>:<pattern>"] [--patch-dir <outdir>]`.

`--repo-src`

The `git-remote-name` can be a name listed by `git remote` combined with the branch name listed by `git branch`. For example, you can provide `origin/master` to extract all commits on this remote source.

`--filter`

The `<git-log-filter-name1>` can be a filter switch without the `--` prefix listed by `git log help`. For example, if you want to filter all the commits by an author using `--author`, you can provide a filter such as `author:someone`. If no filter is given, the latest **10** commits of the given repo source will be used.

`--patch-dir`

The `outdir` will contain all the formatted patch files with the pattern "*commit-hash.patch*" as their names and the manifest file for the summary and maintaining the patches. If  no `outdir` is not specified, the directory name will be "*patch-<5 digit random uuid>*".

### Apply Patches

`apply-patches`

Apply the patches according to the given patch directory and the patch manifest file. You can run this command: `python3 pm.py apply-patches <--patch-dir <path-to-the-patch-dir>> [--branch <branch-name>]`

`--patch-dir`

The `outdir` will contain all the formatted patch files and the manifest file.

`--branch`

When the patches are applied, a new branch will be created. The branch name can be specified by the user. If no name is specified, then the patch directory name will be used.

### About the manifest file

The manifest file is a `json` formatted file contains the summary of the patches. The name is "*Patch_Manifest.json*" and it's hard coded, **should not be modified**.

The following the format of the manifest file:

```
// This file is auto generated, but feel free to modify it according to your needs
[
    {
        "commit": "6233680cad",
        "summary": "nuttx/sched: remove unused group link node",
        "date": "(Wed Mar 6 09:03:18 2024 +0800)",
        "apply": true
    },
    {
        "commit": "8592e7e009",
        "summary": "sched/task: save argument counter to avoid limit check",
        "date": "(Tue Mar 5 12:11:47 2024 +0800)",
        "apply": true
    },
    ...
```

- commit
  - the commit hash
- summary
  - the commit summary
- date
  - the date entry in the commit message
- apply
  - controls whether to apply this patch

### Generate CSV Report File

Generates the report file containing the patch link in a CSV format.

You can run the following command to use this feature.

` python3 pm.py gen-csv-files <--patch-dir <patch-dir>>`

`--patch-dir`

The `outdir` will contain all the formatted patch files and the manifest file.

## TODOs & Limitations

- patch applying order
  - currently we will apply the patches given in the manifest file in a reverse order. However, in the real life, patches may have dependencies, we need to specify the relation chain when we apply them
- convert a remote to a url smartly
  - currently the **CSV report functionality is not finished yet**
