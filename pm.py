import sys
import subprocess
import os
import uuid
import json
import argparse

def run_shell_cmd(cmdlist : list):
    sp = subprocess.run(cmdlist, stdout=subprocess.PIPE)

    if sp.returncode:
        errmsg = f"Failed to execute cmd {' '.join(cmdlist)}"
        print(errmsg)
    
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
        f.write("// This file is auto generated, but feel free to modify it "
       "according to your needs\n")
        json.dump(manifest, f, indent=4)

    return manifest

def gen_formatted_patches(manifest, outdir):

    for m in manifest:
        commit = m.get("commit")

        ret, _, _ = run_shell_cmd(["git", "format-patch", "-1", "--output", f"{outdir}/{commit}.patch", f"{commit}"])

        if ret:
            print(f"Failed to generate patch file for {commit}")

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

def parse_patch_manifest(filename : str):
    manifest = None

    with open(filename, "r") as f:
        no_comments = ""

        for l in f.readlines():
            if l.lstrip(" ").startswith("//"):
                continue
            no_comments += l
        
        manifest = json.loads(no_comments)

    return manifest


def handle_apply_patches(manifest_file : str, branch : str, patch_dir : str):
    manifest = parse_patch_manifest(manifest_file)

    # FIXME: check if we have local uncommitted changes?

    # checkout a new branch for applying the patches
    ret, out, _ = run_shell_cmd(["git", "checkout", "-b", f"{branch}"])

    if ret:
        print(f"Failed to create a new branch {branch}")
        raise RuntimeError("Git failed to create branch")

    print(f"Creating a new branch {branch} for applying the following patches")

    git_apply_patch_cmd = ["git", "am", "-3", "place_holder"]

    # apply the patches one by one, abort on any errors
    # TODO: for now we apply the patches in the reverse order
    # as the first commit in the manifest file is the latest one
    # hence it should be applied at last. In the future, we 
    # should apply patches by the given relation chain! 
    for m in manifest[::-1]:
        # skip any patch that the user doesn't want to apply
        apply = m.get("apply")
        commit = m.get("commit")
        summary = m.get("summary")
        
        print(f"About to {'skip' if not apply else 'apply'} patch {commit} about {summary}...")
        
        if not apply:
            continue

        # find the patch file according to the commit hash
        patch_file = os.path.join(patch_dir, f"{commit}.patch")

        git_apply_patch_cmd[-1] = patch_file


        ret, out, err = run_shell_cmd(git_apply_patch_cmd)

        if ret:
            print(f"Failed to apply patch {commit}")
            print("Due to: ")
            if out:
                print(out.decode())
            if err:
                print(err.decode())
            raise RuntimeError("Git apply patch failed")

        print()

def handle_apply_dry_run():
    pass

def handle_gen_csv_report(manifest_file : str, report_file : str):
    import csv

    manifest = parse_patch_manifest(manifest_file)

    #FIXME: the url is hard coded here

    url_prefix = "https://github.com/realprocrastinator/incubator-nuttx/commit/"

    with open(report_file, 'w', newline='') as f:
        writer = csv.writer(f, delimiter=',', quotechar=',', quoting=csv.QUOTE_MINIMAL)
        
        writer.writerow(["Commit", "Date", "Summary", "Link"])

        for m in manifest:
            writer.writerow([m.get("commit"), m.get("date"), f'\"{m.get("summary")}\"', f'\"{url_prefix + m.get("commit")}\"'])

def main():
    
    args = build_arg_parser().parse_args()

    valid_cmds = {
        "gen-patches" : handle_gen_patches,
        "apply-patches" : handle_apply_patches,
        "apply-dry-run" : handle_apply_dry_run,
        "gen-csv-files" : handle_gen_csv_report,
    }

    if args.command not in valid_cmds:
        raise ValueError("Invalid commands")

    if args.command != "gen-patches" and not args.patch_dir:
        raise ValueError("patch directory must be specified when applying the patches")
    elif not args.repo_src:
        print("WARNING: repo upstream source not specified, using the current worktree as the log source!")

    handler = valid_cmds.get(args.command)

    manifest_file = os.path.join(args.patch_dir, "Patch_Manifest.json")
    
    if args.command == "gen-patches":
        handler(args.patch_dir, args.filter, args.repo_src)
    elif args.command == "gen-csv-files":
        handler(manifest_file, os.path.join(args.patch_dir, "report.csv"))
    else:
        branch = args.branch

        if not branch:
            branch = os.path.basename(os.path.dirname(f"{args.patch_dir}")) # the default branch name will be same as the dir name for holding the patches

        handler(manifest_file, branch, args.patch_dir)

if __name__ == "__main__":
    sys.exit(main())
