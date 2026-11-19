# shellcheck shell=bash disable=SC2329
# dracmon remote script. Piped to `bash -l -s` on a login node, after a
# preamble of plain shell variable assignments:
#   DRACMON_SECTIONS DRACMON_SINCE DRACMON_OFFSETS DRACMON_GLOBS DRACMON_CELLS_RETENTION
#   and optionally DRACMON_USAGE_START DRACMON_USAGE_END (usage window, default
#   the last 7 days: DRAC rejects sacct ranges of 29 days or more on some clusters)
#   and DRACMON_USAGE_TIMEOUT (seconds for the group usage sacct, default 45).
# Runs cheap Slurm queries, prints framed raw output and exits. A failing
# section never stops the others (no set -e). Writes only under
# $SCRATCH/.dracmon/cells (old-log cleanup), and not at all if $SCRATCH is empty.

# Every command runs under timeout 20, except the group usage sacct (t_usage):
# on a loaded login node a 7-day window was seen to exceed 20 s.
case "${DRACMON_USAGE_TIMEOUT:-}" in '' | *[!0-9]*) DRACMON_USAGE_TIMEOUT=45 ;; esac
if command -v timeout >/dev/null 2>&1; then
    t() { timeout 20 "$@"; }
    t_usage() { timeout "$DRACMON_USAGE_TIMEOUT" "$@"; }
else
    t() { "$@"; }
    t_usage() { "$@"; }
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
s_steps() { t sacct -u "$me" -S "$DRACMON_SINCE" -E now -P -n -o JobID,MaxRSS,TotalCPU; }
s_fairshare() { [ -n "$accts" ] || return 3; t sshare -P -n -A "$accts" -u "$me" -o Account,User,RawUsage,EffectvUsage,LevelFS,FairShare; }
s_usage() { [ -n "$accts" ] || return 3; t_usage sacct -X -a -A "$accts" -S "${DRACMON_USAGE_START:-now-7days}" -E "${DRACMON_USAGE_END:-now}" -P -n -o JobID,User,Account,State,Start,Elapsed,AllocTRES; }
s_disk() { t diskusage_report; }
s_partitions() { t sinfo -h -o '%P|%a|%l|%D|%T|%G'; }

s_cells() {
    [ -n "${SCRATCH:-}" ] || return 0
    root=$SCRATCH/.dracmon/cells
    [ -d "$root" ] || return 0
    t find "$root" -name '*.log' -type f 2>/dev/null | sort | while IFS= read -r f; do
        rel=${f#"$root"/}
        size=$(t wc -c <"$f" | tr -d ' ')
        case "$size" in '' | *[!0-9]*) continue ;; esac
        off=$(printf '%s\n' "${DRACMON_OFFSETS:-}" | awk -F'\t' -v r="$rel" '$1 == r { print $2; exit }')
        case "$off" in '' | *[!0-9]*) off=0 ;; esac
        # end: byte offset just after the last complete line. The local side
        # advances to it whatever the filter below drops, so offsets never drift.
        # The new bytes are read ONCE into a temp file (under the cells root, the
        # only place this script writes) bounded by size. A failed, timed-out or
        # short read leaves end = off and sends nothing: the store does not
        # advance and the bytes are read again next poll.
        end=$off
        tmp=
        if [ "$size" -gt "$off" ] && tmp=$(mktemp "$root/.chunk.XXXXXX" 2>/dev/null); then
            t tail -c +$((off + 1)) "$f" 2>/dev/null | head -c $((size - off)) >"$tmp" 2>/dev/null
            got=$(wc -c <"$tmp" | tr -d ' ')
            if [ "$got" = $((size - off)) ]; then
                if [ "$(tail -c 1 "$tmp" | wc -l | tr -d ' ')" = 1 ]; then
                    end=$size
                else
                    # no final newline: the last line is torn, leave it for a later poll
                    torn=$(tail -n 1 "$tmp" | wc -c | tr -d ' ')
                    case "$torn" in '' | *[!0-9]*) torn=$got ;; esac
                    end=$((size - torn))
                fi
            fi
        elif [ "$size" -le "$off" ]; then
            end=$size  # nothing new (or shrunk: the local side resets on size < offset)
        fi
        printf '#file %s %s %s\n' "$size" "$end" "$rel"
        if [ "$end" -gt "$off" ]; then
            # keep only lines starting with a digit (hook lines start with the epoch): this
            # drops anything that could spoof a frame or a #file marker
            head -c $((end - off)) "$tmp" | LC_ALL=C grep '^[0-9]'
        fi
        [ -z "$tmp" ] || rm -f "$tmp"
    done
    t find "$root" -name '*.log' -type f -mtime +"${DRACMON_CELLS_RETENTION:-30}" -delete 2>/dev/null
    # a poll killed mid-read (ssh timeout) can leave a temp chunk behind
    t find "$root" -name '.chunk.*' -type f -mmin +60 -delete 2>/dev/null
    # -mmin +60: a job may have just created its campaign directory
    t find "$root" -mindepth 1 -type d -empty -mmin +60 -delete 2>/dev/null
    return 0
}

# count_glob PATTERN: matches of a stored done_glob. A leading $SCRATCH/, $HOME/
# or ~/ is expanded here with case (never eval); other patterns are relative
# to $HOME. The pattern itself is only ever globbed, never evaluated.
# shellcheck disable=SC2016,SC2088
count_glob() {
    case $1 in
        '$SCRATCH/'*)
            [ -n "${SCRATCH:-}" ] || { echo 0; return 0; }
            base=$SCRATCH pat=${1#'$SCRATCH/'} ;;
        '$HOME/'*) base=$HOME pat=${1#'$HOME/'} ;;
        '~/'*) base=$HOME pat=${1#'~/'} ;;
        *) base=$HOME pat=$1 ;;
    esac
    t bash -c 'cd "$1" 2>/dev/null || exit 0
        IFS=
        c=0
        for p in $2; do
            if [ -e "$p" ] || [ -L "$p" ]; then c=$((c + 1)); fi
        done
        echo "$c"' _ "$base" "$pat"
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
