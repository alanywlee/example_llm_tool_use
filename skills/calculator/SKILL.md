# calculator

## Purpose

Use this skill when deterministic numerical calculation is needed.

## When to use

Use this skill when:
- The answer requires arithmetic.
- The user asks for percentage, ratio, average, total, discount, tax, or comparison.
- The answer depends on exact numbers from retrieved KM evidence.

## Required tools

- calculator__calculate

## Workflow

1. Extract only the necessary numbers from the user query or retrieved evidence.
2. Convert the request into a precise expression.
3. Call calculator__calculate.
4. Use the result to answer in natural language.
5. Mention rounding if relevant.
