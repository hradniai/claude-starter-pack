#!/usr/bin/env bash
# Claude Code statusLine — 3-line layout, columned via terminal width.
# Reads JSON from stdin (per Claude Code statusline contract).

input=$(cat)

RESET=$'\033[0m'
CYAN=$'\033[36m'
YELLOW=$'\033[33m'
GREEN=$'\033[32m'
RED=$'\033[31m'
MAGENTA=$'\033[35m'
DIM=$'\033[2m'

WIDTH=${COLUMNS:-$(tput cols 2>/dev/null || echo 100)}

jqr() { printf '%s' "$input" | jq -r "$1 // empty" 2>/dev/null; }

visual_len() {
  local s="$1"
  local stripped
  stripped=$(printf '%s' "$s" | sed $'s/\033\\[[0-9;]*m//g')
  printf '%s' "${#stripped}"
}

pad_right() {
  local left="$1" right="$2" width="$3"
  local ll rr pad
  ll=$(visual_len "$left")
  rr=$(visual_len "$right")
  pad=$(( width - ll - rr ))
  (( pad < 1 )) && pad=1
  printf '%s%*s%s' "$left" "$pad" "" "$right"
}

# ── Data ─────────────────────────────────────────────────────────────────────
model_name=$(jqr '.model.display_name')
effort_level=$(jqr '.effort.level')
output_style=$(jqr '.output_style.name')
[[ -z "$output_style" ]] && output_style="default"

project_dir=$(jqr '.workspace.project_dir')
current_dir=$(jqr '.workspace.current_dir')
project_name=$(basename "${project_dir:-$current_dir}" 2>/dev/null)

cost_usd=$(jqr '.cost.total_cost_usd')

worktree_name=$(jqr '.worktree.name')
agent_name=$(jqr '.agent.name')

total_input=$(jqr '.context_window.total_input_tokens')
total_output=$(jqr '.context_window.total_output_tokens')
ctx_size=$(jqr '.context_window.context_window_size')
ctx_pct=$(jqr '.context_window.used_percentage')

five_pct=$(jqr '.rate_limits.five_hour.used_percentage')
five_reset=$(jqr '.rate_limits.five_hour.resets_at')
seven_pct=$(jqr '.rate_limits.seven_day.used_percentage')
seven_reset=$(jqr '.rate_limits.seven_day.resets_at')

# Git branch — ask git directly using project_dir
git_branch=""
if [[ -n "$project_dir" && -d "$project_dir" ]]; then
  git_branch=$(git -C "$project_dir" symbolic-ref --short HEAD 2>/dev/null)
fi
[[ -z "$git_branch" ]] && git_branch=$(jqr '.worktree.branch')

# ── Line 1: model · effort · output_style                            $cost ──
model_str="${CYAN}${model_name}${RESET}"

effort_str=""
if [[ -n "$effort_level" ]]; then
  case "$effort_level" in
    high|max|xhigh) effort_str=" ${DIM}·${RESET} effort:${YELLOW}${effort_level}${RESET}" ;;
    *)              effort_str=" ${DIM}·${RESET} effort:${effort_level}" ;;
  esac
fi

style_str=" ${DIM}·${RESET} ${output_style}"

agent_str=""
[[ -n "$agent_name" ]] && agent_str=" ${DIM}·${RESET} ${GREEN}▶ ${agent_name}${RESET}"

line1_left="${model_str}${effort_str}${style_str}${agent_str}"

cost_str=""
if [[ -n "$cost_usd" && "$cost_usd" != "null" ]]; then
  cost_fmt=$(awk -v c="$cost_usd" 'BEGIN{printf "%.2f", c}')
  cost_color=$(awk -v c="$cost_usd" 'BEGIN{
    if (c<1) print "G"; else if (c<=5) print "Y"; else print "R"
  }')
  case "$cost_color" in
    G) col=$GREEN ;; Y) col=$YELLOW ;; R) col=$RED ;;
  esac
  cost_str="${col}\$${cost_fmt}${RESET}"
fi

# Session throughput (kumulativně, včetně subagentů)
fmt_tok() {
  awk -v t="${1:-0}" 'BEGIN{
    if (t >= 1000000) printf "%.1fM", t/1000000
    else if (t >= 1000) printf "%.0fk", t/1000
    else printf "%d", t
  }'
}
throughput_str=""
if [[ -n "$total_input" && "$total_input" != "null" ]] || \
   [[ -n "$total_output" && "$total_output" != "null" ]]; then
  in_fmt=$(fmt_tok "$total_input")
  out_fmt=$(fmt_tok "$total_output")
  throughput_str="${DIM}${in_fmt}↑ ${out_fmt}↓${RESET}"
fi

# Right side: throughput · cost
right1=""
if [[ -n "$throughput_str" && -n "$cost_str" ]]; then
  right1="${throughput_str} ${DIM}·${RESET} ${cost_str}"
elif [[ -n "$cost_str" ]]; then
  right1="$cost_str"
elif [[ -n "$throughput_str" ]]; then
  right1="$throughput_str"
fi

if [[ -n "$right1" ]]; then
  line1=$(pad_right "$line1_left" "$right1" "$WIDTH")
else
  line1="$line1_left"
fi

# ── Line 2: project ⎇ branch                              ctx: Xk/Yk (Z%) ──
wt_str=""
[[ -n "$worktree_name" ]] && wt_str=" ${DIM}[wt:${RESET}${MAGENTA}${worktree_name}${RESET}${DIM}]${RESET}"
branch_str=""
[[ -n "$git_branch" ]] && branch_str=" ${MAGENTA}⎇ ${git_branch}${RESET}"
line2_left="${project_name}${wt_str}${branch_str}"

ctx_str=""
if [[ -n "$ctx_pct" && "$ctx_pct" != "null" ]]; then
  pct_int=$(awk -v p="$ctx_pct" 'BEGIN{printf "%.0f", p}')
  # Aktuální použití okna = pct × ctx_size (NE total_input_tokens, to je kumulativní za session)
  used_k=$(awk -v p="$ctx_pct" -v s="${ctx_size:-0}" 'BEGIN{printf "%.0f", p/100*s/1000}')
  total_k=$(awk -v s="${ctx_size:-0}" 'BEGIN{printf "%.0f", s/1000}')
  if   (( pct_int < 50 )); then ctx_color=$GREEN
  elif (( pct_int < 80 )); then ctx_color=$YELLOW
  else                          ctx_color=$RED
  fi
  ctx_str="ctx: ${ctx_color}${used_k}k/${total_k}k (${pct_int}%)${RESET}"
fi

if [[ -n "$ctx_str" ]]; then
  line2=$(pad_right "$line2_left" "$ctx_str" "$WIDTH")
else
  line2="$line2_left"
fi

# ── Line 3: 5h: X%                                        [reset in Xh Ym] ──
line3=""
if [[ -n "$five_pct" && "$five_pct" != "null" ]]; then
  pct5=$(awk -v p="$five_pct" 'BEGIN{printf "%.0f", p}')
  if   (( pct5 < 50 )); then col5=$GREEN
  elif (( pct5 < 80 )); then col5=$YELLOW
  else                       col5=$RED
  fi
  five_left="5h: ${col5}${pct5}%${RESET}"

  # Inline reset countdown — always shown.
  # Red warning when pct5 >= 80 AND > 1h remaining (vysoká spotřeba s dlouhou session = signál zpomalit)
  if [[ -n "$five_reset" && "$five_reset" != "null" ]]; then
    now=$(date +%s)
    rem=$(( five_reset - now ))
    if (( rem > 0 )); then
      hrs=$(( rem / 3600 ))
      mins=$(( (rem % 3600) / 60 ))
      if (( hrs > 0 )); then
        timer="reset in ${hrs}h ${mins}m"
      else
        timer="reset in ${mins}m"
      fi
      if (( pct5 >= 80 && rem > 3600 )); then
        five_left="${five_left} ${DIM}(${RESET}${RED}${timer}${RESET}${DIM})${RESET}"
      else
        five_left="${five_left} ${DIM}(${timer})${RESET}"
      fi
    fi
  fi

  # Right side: 7d ahead-of-pace
  right_str=""
  if [[ -n "$seven_pct" && "$seven_pct" != "null" \
       && -n "$seven_reset" && "$seven_reset" != "null" ]]; then
    now=$(date +%s)
    week=604800
    win_start=$(( seven_reset - week ))
    elapsed=$(( now - win_start ))
    if (( elapsed > 0 && elapsed < week )); then
      # Expected % at linear pace
      expected=$(awk -v e="$elapsed" -v w="$week" 'BEGIN{printf "%.2f", e/w*100}')
      ahead=$(awk -v u="$seven_pct" -v x="$expected" 'BEGIN{print (u>x)?1:0}')
      if (( ahead == 1 )); then
        pct7=$(awk -v p="$seven_pct" 'BEGIN{printf "%.0f", p}')
        # Color by ratio: <1.3x mírně napřed=žlutá, >=1.3x výrazně=červená
        ratio=$(awk -v u="$seven_pct" -v x="$expected" 'BEGIN{print (x>0)?u/x:1}')
        sev=$(awk -v r="$ratio" 'BEGIN{print (r>=1.3)?"R":"Y"}')
        case "$sev" in R) col7=$RED ;; Y) col7=$YELLOW ;; esac
        # Reset countdown (days + hours, or hours + minutes if <1d)
        rem7=$(( seven_reset - now ))
        if (( rem7 > 0 )); then
          d7=$(( rem7 / 86400 ))
          h7=$(( (rem7 % 86400) / 3600 ))
          m7=$(( (rem7 % 3600) / 60 ))
          if (( d7 > 0 )); then
            reset7="reset in ${d7}d ${h7}h"
          elif (( h7 > 0 )); then
            reset7="reset in ${h7}h ${m7}m"
          else
            reset7="reset in ${m7}m"
          fi
          right_str="7d: ${col7}${pct7}%${RESET} ${DIM}(${reset7})${RESET}"
        else
          right_str="7d: ${col7}${pct7}%${RESET}"
        fi
      fi
    fi
  fi

  if [[ -n "$right_str" ]]; then
    line3=$(pad_right "$five_left" "$right_str" "$WIDTH")
  else
    line3="$five_left"
  fi
fi

printf '%s\n' "$line1"
printf '%s\n' "$line2"
[[ -n "$line3" ]] && printf '%s' "$line3"
