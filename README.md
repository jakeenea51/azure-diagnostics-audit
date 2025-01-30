# Azure Diagnostics Audit
Python script for auditing the diagnostic settings of your Azure resources.

This script was designed to make it easier to assess and verify your organization's logging strategy across your entire Azure tenant. 

The script allows you to audit your Azure resources' diagnostic settings based on:
- Resource type
- Diagnostic setting name
- Target log analytics workspace (where the logs are being sent)
- Subscription ID


## Requirements
You must have the Azure CLI installed for this script to work. Installation instructions can be found [here](https://learn.microsoft.com/en-us/cli/azure/install-azure-cli). Once installed, login to Azure by running the command `az login`.

Ensure all Python requirements are installed by running the command `pip install -r requirements.txt`.


## Usage
```
diag_audit.py [-h] -s SUBSCRIPTIONS -t {appservice,aks} [-d DIAGNOSTIC] [-w WORKSPACE]
```
> At least one of either DIAGNOSTIC or WORKSPACE must be present.
- `-s`/`--subscriptions`: (filepath) Audit one or more subscriptions. Input must be in the form of a CSV, with each line containing the subscription ID and name. For an example, check out 'subscriptions-example.csv'.
- `-t`/`--type`:  (string) The resource type you are auditing. Current options are 'appservice' or 'aks'.
- `-d`/`--diagnostic`: (string) The name of the diagnostic setting you are looking for.
- `-w`/`--workspace`: (string) The name of the log analytics workspace where you are collecting your logs.
- `-h`: Help
