import sys
import subprocess
import os
import uuid
import json
import argparse

def errprint(msg : str):
    print(msg)

def run_shell_cmd(cmdlist : list):
    sp = subprocess.run(cmdlist, stdout=subprocess.PIPE)

    if sp.returncode:
        errmsg = f"Failed to execute cmd {' '.join(cmdlist)}"
        errprint(errmsg)
    
    return (sp.returncode, sp.stdout, sp.stderr)

def do_upstream_fetch(remote : str):
    cmd = ["git", "fetch", remote]

    ret, _, _ = run_shell_cmd(cmd)

    if ret:
        raise RuntimeError("Git fetch failed")

def parse_formatted_log(log : str) -> list:
    summary = [tuple([t.rstrip(" \"\n").lstrip(" \"\n") \
        for t in e.split("@@@")]) \
        for e in [l for l in log.splitlines()]]

    return summary


def commits_filter_by(filters : list, repo_src) -> list:
    
    # Hope @@@ can be used as the delima safely :)
    # hash @@@ summary @@@ date
    fmt = "%h @@@ %s @@@ (%ad)"

    git_log_cmd = ["git", "log"]

    if repo_src:
        git_log_cmd.append(repo_src)

    cmd = git_log_cmd + filters + [f"--pretty=format:\"{fmt}\""]
    
    ret, out, _ = run_shell_cmd(cmd)

    if ret:
        raise RuntimeError("Failed to show git logs")

    summarys = parse_formatted_log(out.decode())

    # after parsing, we will get a list of tuples, each tuple
    # has the following structure (hash, description, date)

    return summarys

def gen_patch_manifest(summarys, outdir, gen_template=False) -> list:
    if gen_template:
        raise ValueError("Not implemented yet")
    
    manifest = []

    for hash, desc, date in summarys:
        manifest.append({
            "commit" : hash,
            "summary" : desc,
            "date" : date,
            "apply" : True
        })
    
    with open(os.path.join(outdir, "Patch_Manifest.json"), "w") as f:
        f.write("// This file is auto generated, but feel free to modify it"
       "according to your needs\n")
        json.dump(manifest, f, indent=4)

    return manifest

def gen_formatted_patches(manifest, outdir):

    for m in manifest:
        commit = m.get("commit")

        ret, _, _ = run_shell_cmd(["git", "format-patch", "-1", "--output", f"{outdir}/{commit}.patch", f"{commit}"])

        if ret:
            errprint(f"Failed to generate patch file for {commit}")

def build_arg_parser():
    parser = argparse.ArgumentParser(description="This is a tool for easily managing your patches")

    parser.add_argument("--patch-dir", help="Specifying the output directory for holding the filtered patches")
    
    parser.add_argument("--repo-src", help="Specifying the upstream repo soruce for generating patches, the src can be either a url link or a remote name")

    parser.add_argument("--filter", help="Applying the filter rule to when generating the patches, the rules are same as the git log filters, if not filters are given the latest 10 commits will be used")

    parser.add_argument("--branch", help="Specifying the branch name when applying the patches")

    parser.add_argument("command", help="Specifying the operatin that the patch manager should take, it can be <gen-patches | apply-patches | apply-dry-run>")

    return parser

def parse_filter(rules : str) -> list:
    # TODO: For now we onlt support limited filters, namely --author and --since

    # ";" are used to speperate different filters
    try:
        filter_grp = rules.split(";")
    except Exception as e:
        print("Failed to parse filter rule: ", e)
        print("Default rules are applied")
        return []

    # each filter rule has the format: filter_name:pattern,
    # and the filter_name will be prefixed by "--" to transfer into# a git log switch
    filters = []

    try:
        for f in filter_grp:
            name, pattern = f.split(":")
            filters += ["--" + name, pattern]
    except Exception as e:
        print("Failed to parse filter group: ", e)
        print("The default rule will apply")
        return []

    print(filters)

    return filters

def handle_gen_patches(patch_dir, filter, repo_src):
    if not patch_dir:
        patch_dir = "-".join(("patches", str(uuid.uuid1())[:7]))

    filter_rules = parse_filter(filter)

    if not filter_rules:
        filter_rules = ["-10"] # limit the commit log to 10

    summarys = commits_filter_by(filter_rules, repo_src)
    
    os.mkdir(patch_dir)

    print(f"The patch directory is located at: {patch_dir}")

    m = gen_patch_manifest(summarys, patch_dir)
    gen_formatted_patches(m, patch_dir)


def handle_apply_patches():
    pass

def handle_apply_dry_run():
    pass

def main():
    
    args = build_arg_parser().parse_args()

    valid_cmds = {
        "gen-patches" : handle_gen_patches,
        "apply-patches" : handle_apply_patches,
        "apply-dry-run" : handle_apply_dry_run,
    }

    if args.command not in valid_cmds:
        raise ValueError("Invalid commands")

    if args.command != "gen-patches" and not args.patch_dir:
        raise ValueError("patch directory must be specified when applying the patches")
    elif not args.repo_src:
        raise ValueError("repo upstream source must be specified when generating patches")

    handler = valid_cmds.get(args.command)

    if args.command == "gen-patches":
        handler(args.patch_dir, args.filter, args.repo_src)
    else:
        handler(args.patch_dir)

if __name__ == "__main__":
    sys.exit(main())