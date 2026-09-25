# Compact crystal experience — 2026-09-16

Implemented in `desktop/experience.py`, using the existing native UI and cached
artwork. The main launcher now uses this presentation. The original `Desktop`
remains the tested base for command execution and permission boundaries.

## Interaction

1. Launch: centered baked crystal and “LYA online · Guest mode” for 1.6 seconds.
2. A 420ms shrink/move docks a 64 x 88 transparent crystal control near the edge.
3. Click the crystal: a 460 x 90 glass input strip opens.
4. Enter a command: a 460 x 290 response card opens. Long text scrolls.
5. `open chat`: a 520 x 540 workspace with a bounded display transcript.
6. `show files`: existing allowlisted project documents in the expanded view.
7. Stop/Escape/close: compact mode; transient transcript clears. Quit exits.

Transcript is display-only RAM, limited to six question/answer pairs, with each
stored answer limited to 8,000 characters. This does not add model conversation
memory or persistence. Real identity and voice remain pending. Greeting is guest.

## Resource choices

- The owner's GLB uses its already-baked transparent image; no live GLB/OpenGL
  renderer is loaded by the application. The owner requested this artwork for the
  new experience. `--original-art` retains the earlier artwork alternative.
- Existing finite drift/color transitions and cached tints are reused. Idle drift
  stops; hidden text reveal stops. Existing slow-paint fallback remains active.
- Answer reveal updates in chunks every 40ms for at most about 0.8 seconds for
  ordinary responses. Reduced motion displays the whole answer immediately.
- No continuous rotation, desktop sampling, blur capture or new dependencies.
- Reduced motion disables docking movement and text reveal. It also stops an
  in-progress panel fade/move. Actual battery life and display FPS are unmeasured.

## Validation

- Existing 57 baseline checks passed after integrating the new main entry point.
- Five new isolated tests passed: intro/dock/input/answer/chat; private denial and
  stale cancellation; interrupted reveal/reduced motion; screen bounds/files; and
  completed docking with no further idle orb paints in the observation interval.
- `desktop/check_experience.py` generates synthetic previews. `input.png`,
  `answer.png` and `chat.png` were inspected for readable layout. Their manually
  arranged positions illustrate components, not actual monitor anchoring.
- No live provider call, camera, microphone, enrollment or deployment was tested.

## Try it

Quit the existing LYA instance, then run `launch-lya.cmd`. Wait for docking, click
the crystal and type `time`, `who am i` or `open chat`. For the least animation,
run `launch-lya.cmd --original-art --reduced-motion`.

Run `check-t01.cmd` for baseline plus compact experience checks. The current total
is 62 checks; the runner stops on a failed suite. Inspect each suite's result.
