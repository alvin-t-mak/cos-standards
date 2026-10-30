# Build the workbook

A person runs the build script and checks the file it writes.

## Sub-features

- Run the build for <app> from the repo root.
- Open the workbook or other generated file.
- Read the cells or fields a person would check.

## How to get to it (user POV)

From the repo root, run the build the way a person does. There is no test-only entry point.

## Driving it with <harness>

Run `<command>`. Open the generated file and compare the values to the inputs. The end state is those values, recorded under `<evidence-dir>`.

## Gotchas

If an input the script needs is missing, the drive fails and the reason is recorded here. Do not stub the output file to make the run pass.
