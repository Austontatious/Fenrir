# Evaluation Conditions

## raw_minimal

Minimal orchestration for interface sanity checks. Keeps instruction overhead low.

## eval_control

Neutral measurement-oriented wrapper. Standardizes structure and uncertainty handling without heavy policy preload.

## production_wrapper

Loads a production prompt wrapper to compare behavior against `eval_control` and isolate wrapper dependence.

## eval_control_stress

Same baseline control framing plus pressure-style item presentation to probe format stability and fragility.
