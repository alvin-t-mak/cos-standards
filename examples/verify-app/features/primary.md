# Primary

The main path a person takes through <app>.

## Sub-features

- Open the primary screen of <app>.
- Complete the one action a person came here to do.
- See the result on that same screen.

## How to get to it (user POV)

Open <app> and go to the primary screen the way a person does, with no test-only route.

## Driving it with <harness>

Run `<command> drive`. The end state is the one a person can see, and the side effect is recorded under `<evidence-dir>`.

## Gotchas

If a precondition is missing, the drive fails and the reason is recorded here. Do not weaken the drive to make it pass.
