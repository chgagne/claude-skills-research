# shellcheck shell=bash disable=SC2329
# dracmon remote script. Piped to `bash -l -s` on a login node, after a
# preamble of plain shell variable assignments:
#   DRACMON_SECTIONS DRACMON_SINCE DRACMON_OFFSETS DRACMON_GLOBS DRACMON_CELLS_RETENTION
# Runs cheap Slurm queries, prints framed raw output and exits. A failing
# section never stops the others (no set -e). Writes only under
# $SCRATCH/.dracmon/cells (old-log cleanup), and not at all if $SCRATCH is empty.

if command -v timeout >/dev/null 2>&1; then
    t() { timeout 20 "$@"; }
else
    t() { "$@"; }
fi

want() {
    case " ${DRACMON_SECTIONS:-} " in *" $1 "*) return 0 ;; esac
    return 1
}

# frame NAME FUNCTION: run FUNCTION, print the frame; leaves rc in $rc, output in $out.
frame() {
    name=$1
    out=$("$2" 2>/dev/null)
    rc=$?
    printf '@@dracmon begin %s\n' "$name"
    [ -z "$out" ] || printf '%s\n' "$out"
    printf '@@dracmon end %s rc=%s\n' "$name" "$rc"
}

s_env() {
    printf 'user=%s\n' "${USER:-$(id -un)}"
    printf 'cluster=%s\n' "${CC_CLUSTER:-}"
    printf 'scratch=%s\n' "${SCRATCH:-}"
    printf 'host=%s\n' "$(hostname)"
    printf 'now=%s\n' "$(date +%s)"
    printf 'tz=%s\n' "$(date +%z)"
}
s_accounts() {
    raw=$(t sacctmgr -n -P show assoc user="$me" format=Account)
    r=$?
    printf '%s\n' "$raw" | sort -u
    return "$r"
}
s_queue() { t squeue -u "$me" -h -o '%i|%A|%F|%K|%j|%P|%T|%M|%l|%S|%C|%m|%b|%R|%a|%V'; }
s_accounting() {
    t sacct -X -u "$me" -S "$DRACMON_SINCE" -E now -P -n \
        -o JobID,JobName,Account,Partition,State,ExitCode,Elapsed,Timelimit,Submit,Start,End,NodeList,AllocTRES,ReqMem,TotalCPU,NCPUS
}
s_steps() { t sacct -u "$me" -S "$DRACMON_SINCE" -E now -P -n -o JobID,MaxRSS; }
s_fairshare() { t sshare -P -n -A "$accts" -u "$me" -o Account,User,RawUsage,EffectvUsage,LevelFS,FairShare; }
s_usage() { t sacct -X -a -A "$accts" -S now-30days -E now -P -n -o JobID,User,Account,State,Start,Elapsed,AllocTRES; }
s_disk() { t diskusage_report; }
s_partitions() { t sinfo -h -o '%P|%a|%l|%D|%T|%G'; }

s_cells() {
    [ -n "${SCRATCH:-}" ] || return 0
    root=$SCRATCH/.dracmon/cells
    [ -d "$root" ] || return 0
    find "$root" -name '*.log' -type f 2>/dev/null | sort | while IFS= read -r f; do
        rel=${f#"$root"/}
        size=$(wc -c <"$f" | tr -d ' ')
        off=$(printf '%s\n' "${DRACMON_OFFSETS:-}" | awk -F'\t' -v r="$rel" '$1 == r { print $2; exit }')
        case "$off" in '' | *[!0-9]*) off=0 ;; esac
        printf '#file %s %s\n' "$rel" "$size"
        if [ "$size" -gt "$off" ]; then
            tail -c +$((off + 1)) "$f"
            # keep the next marker on its own line even if the log lacks a final newline
            [ "$(tail -c 1 "$f" | wc -l | tr -d ' ')" = 1 ] || printf '\n'
        fi
    done
    find "$root" -name '*.log' -type f -mtime +"${DRACMON_CELLS_RETENTION:-30}" -delete 2>/dev/null
    find "$root" -mindepth 1 -type d -empty -delete 2>/dev/null
    return 0
}

s_globs() {
    printf '%s\n' "${DRACMON_GLOBS:-}" | while IFS="$(printf '\t')" read -r campaign pattern; do
        [ -n "$campaign" ] || continue
        n=0
        if [ -n "$pattern" ]; then
            n=$(
                cd "$HOME" 2>/dev/null || exit 0
                IFS=
                c=0
                # shellcheck disable=SC2086
                for p in $pattern; do
                    if [ -e "$p" ] || [ -L "$p" ]; then c=$((c + 1)); fi
                done
                echo "$c"
            )
        fi
        printf '#glob %s %s\n' "$campaign" "${n:-0}"
    done
}

me=${USER:-$(id -un)}
accts=

frame env s_env
if want fairshare || want usage || want accounts; then
    frame accounts s_accounts
    accts=$(printf '%s\n' "$out" | paste -sd, -)
fi
for sec in queue accounting steps fairshare usage disk partitions cells globs; do
    want "$sec" && frame "$sec" "s_$sec"
done
exit 0
