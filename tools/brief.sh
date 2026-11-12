# The prompt a video's generating agent is started with, and the only thing it is started with.
#   bash tools/brief.sh <video>
# A video is made by one agent that has the video's brief, DESIGN.md and the inputs, and no history. The
# conversation that starts it is the wrong place to make the video from: it holds the old version, the
# user's reactions to it, drafts that were thrown away and whatever was being argued about an hour ago, so
# a video written there is written partly from all of that. Then the pipeline cannot be judged -- a good
# video may be good because the context carried it, and a bad one may be bad for the same reason. Hand the
# agent this and read what comes back: that is the pipeline's own output. (capstone's two rebuilds are the
# case: the first lost the walkthrough format because the brief did not carry it, and the second kept the
# old video's narration word for word because the narration was sitting in the conversation's context and
# nobody had written down that the words were an output, not an input.)
V=${1:?usage: bash tools/brief.sh <video>}
R="$(cd "$(dirname "$0")/.." && { pwd -W 2>/dev/null || pwd; })"   # the native path: the agent reads files with it
[ -f "$R/$V/brief.md" ] || { echo "no $V/brief.md: write the video's inputs down before starting an agent" >&2; exit 2; }
# tools/prep.sh leaves the choices that are the user's as TODO lines; an agent started on one would take a default
# nobody chose (geant4's audience, format and length were all assumed, because only a PDF was handed over)
if grep -n "TODO" "$R/$V/brief.md" >&2; then echo "$V/brief.md still has the TODO lines above: decide them first" >&2; exit 2; fi
cat <<PROMPT
Make the narrated explainer video in $V, start to finish, on your own.

Read DESIGN.md first -- Part I and Part II are the rules every frame is judged by, Part III is the
workflow you follow step by step. Then read $V/brief.md: that video's source, its audience, the format it
is in, and what has already been cut out of its source for you. Then do Part III, steps 1 to 8, for $V.

Show, don't tell (Part I §1, the first rule): every event, piece of physics, calculation and geometry the
narration describes happens on screen -- it moves, flows, builds or is measured -- rather than being named
beside a still picture. Hold your plan and your writers to it. Where the thing has a shape (a detector, a
geometry, a field, a surface), stage that scene in 3D (Part I §5, "Reach for 3D"): ManimGX makes it cheap.

Those two files and the inputs the brief names are your priors, and nothing else is. An earlier version
of this video may exist in git, or in the folder, or in the conversation that started you. You are not to
read it, ask for it, or render it. Where you catch yourself about to copy a decision instead of making
one, that is the thing this agent exists to prevent.

The repository is $R; it is a local git repository with no remote. Render in WSL through the .sh files
(Part III steps 4 to 7); never above 1080p. You may start scene writers of your own once $V/plan.md is
written -- a writer needs the plan, the palette and the helper inventory, not the source -- and they work
in their own copy of the folder, checked by path. Start them on a cheaper model: what makes one writer per
scene affordable is that the plan has already decided what the scene does.

Mark the phases as you pass them, so the build times itself:
\`python tools/timelog.py mark $V <phase>\` with received, figures, script, check, render, sent in order
(renders log themselves). A phase is marked once, when it ends.

Before splitting the plan for writers, run \`python -m vlint plan ../$V/plan.md --check\` from tools/ and clear it.

Hand back when the video is rendered at -qh, every gate is clear (static, runtime and the join), you have
read the review sheets and watched the joined file, and you have folded what the video
taught you into the DESIGN.md rule it sharpens (§0: fold, don't log -- no per-video entry). Report what you made, what you decided and what you are unsure of, in 15 lines or fewer. Work
fast and keep your writers' prompts short. Time the script phase (plan, narration, scene writing), name the two or
three things that slowed it most and what would cut them, apply the quick safe ones and list the rest. Do not commit.
PROMPT
