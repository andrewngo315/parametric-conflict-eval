# Basic Evaluation Harness

## What it does

This harness scores hypothetical model answers against its ground truth, imported from examples.json. It measures the accuracy rate, precision, recall and F1 scores of the fake model. It asserts that the accuracy rate of one instance where the model matches ground truth and one instance where it doesn't must be 50%, to ensure that the scorer is correct. 

## How to run

Type the following command in your terminal: python3 harness.py

## Status

The harness is able to accurately score what is intended as outlined in 'what it does' for the fake data but it is not yet equipped with real examples. 
