# shellcheck shell=bash disable=SC2329
# dracmon remote script. Piped to `bash -l -s` on a login node, after a
# preamble of plain shell variable assignments:
#   DRACMON_SECTIONS DRACMON_SINCE DRACMON_OFFSETS DRACMON_GLOBS DRACMON_CELLS_RETENTION
#   and optionally DRACMON_USAGE_START DRACMON_USAGE_END (usage window, default
#   the last 7 days: DRAC rejects sacct ranges of 29 days or more on some clusters).
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
s_fairshare() { [ -n "$accts" ] || return 3; t sshare -P -n -A "$accts" -u "$me" -o Account,User,RawUsage,EffectvUsage,LevelFS,FairShare; }
s_usage() { [ -n "$accts" ] || return 3; t sacct -X -a -A "$accts" -S "${DRACMON_USAGE_START:-now-7days}" -E "${DRACMON_USAGE_END:-now}" -P -n -o JobID,User,Account,State,Start,Elapsed,AllocTRES; }
s_disk() { t diskusage_report; }
s_partitions() { t sinfo -h -o '%P|%a|%l|%D|%T|%G'; }

s_cells() {
    [ -n "${SCRATCH:-}" ] || return 0
    root=$SCRATCH/.dracmon/cells
    [ -d "$root" ] || return 0
    t find "$root" -name '*.log' -type f 2>/dev/null | sort | while IFS= read -r f; do
        rel=${f#"$root"/}
        size=$(t wc -c <"$f" | tr -d ' ')
        off=$(printf '%s\n' "${DRACMON_OFFSETS:-}" | awk -F'\t' -v r="$rel" '$1 == r { print $2; exit }')
        case "$off" in '' | *[!0-9]*) off=0 ;; esac
        printf '#file %s %s\n' "$size" "$rel"
        if [ "$size" -gt "$off" ]; then
            # keep only lines starting with a digit (hook lines start with the epoch): this drops
            # anything that could spoof a frame or a #file marker; send complete lines only
            if [ "$(t tail -c 1 "$f" | wc -l | tr -d ' ')" = 1 ]; then
                t tail -c +$((off + 1)) "$f" | LC_ALL=C grep '^[0-9]'
            else
                # no final newline: the last line is torn, drop it (re-read next poll)
                t tail -c +$((off + 1)) "$f" | sed '$d' | LC_ALL=C grep '^[0-9]'
            fi
        fi
    done
    t find "$root" -name '*.log' -type f -mtime +"${DRACMON_CELLS_RETENTION:-30}" -delete 2>/dev/null
    t find "$root" -mindepth 1 -type d -empty -delete 2>/dev/null
    return 0
}

# shellcheck disable=SC2016
count_glob() {
    t bash -c 'cd "$HOME" 2>/dev/null || exit 0
        IFS=
        c=0
        for p in $1; do
            if [ -e "$p" ] || [ -L "$p" ]; then c=$((c + 1)); fi
        done
        echo "$c"' _ "$1"
}

s_globs() {
    printf '%s\n' "${DRACMON_GLOBS:-}" | while IFS="$(printf '\t')" read -r campaign pattern; do
        [ -n "$campaign" ] || continue
        n=0
        [ -z "$pattern" ] || n=$(count_glob "$pattern")
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
