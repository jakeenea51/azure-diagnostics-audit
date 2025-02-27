# usage: diag_audit.py [-h] -s SUBSCRIPTIONS -t {appservice,aks} [-d DIAGNOSTIC] [-w WORKSPACE]
# at least one of either DIAGNOSTIC or WORKSPACE must be present


# TODO: 
# - add ability to export complete report to a file


from azure.identity import DefaultAzureCredential
from azure.mgmt.resource import ResourceManagementClient
from azure.mgmt.monitor import MonitorManagementClient
from tqdm import tqdm
import argparse
import pathlib
import csv


# Set up args
def parse_args():
    ap = argparse.ArgumentParser()
    ap.add_argument("-s", "--subscriptions", type=pathlib.Path, required=True, help="Audit one or more subscriptions. Input must be in the form of a CSV, with each line containing the subscription ID and name. For an example, check out 'subscriptions-example.csv'.")
    ap.add_argument("-t", "--type", type=str, required=True, choices=["appservice", "aks", "sqldb"], help="The resource type you are auditing.")
    ap.add_argument("-d", "--diagnostic", type=str, help="The name of the diagnostic setting you are looking for.")
    ap.add_argument("-w", "--workspace", type=str, help="The name of the log analytics workspace where you are collecting your logs.")
    return ap.parse_args()


# Terminal output formatting
def prGreen(line): print(f"\033[92m{line}\033[00m") 
def prRed(line): print(f"\033[91m{line}\033[00m") 
def prYellow(line): print(f"\033[1;33m{line}\033[00m") 


# Get Azure credentials using DefaultAzureCredential. If this fails, run Connect-AzAccount in a PowerShell terminal
def get_credentials():
    try:
        return DefaultAzureCredential()
    except Exception as e:
        print(f"Error obtaining Azure credentials: {e}")
        exit(1)


# Retrieve all resources in the subscription
def get_resources(resource_client, resource_type):
    prYellow("\n----------------------------------------------------------\n")
    print("[+] Fetching all resources...")
    resources_results = []
    resources = resource_client.resources.list()
    for resource in resources:
        # App Service
        if resource_type == "appservice":
            if resource.type == "Microsoft.Web/sites" and resource.kind in ["app", "app,linux", "app,linux,container", "app,container,windows"]:
                resources_results.append(resource)
        # AKS
        elif resource_type == "aks":
            if resource.type == "Microsoft.ContainerService/managedClusters":
                resources_results.append(resource)
        # SQL DB
        elif resource_type == "sqldb":
            if resource.type == "Microsoft.Sql/servers/databases":
                resources_results.append(resource)
    return resources_results


# Fetch diagnostic settings for a specific resource
def get_diagnostic_settings(monitor_client, resources, subName, subProgress, setting_name=None, workspace=None):
    matching_diagnostic_settings = {}
    print(f"[+] Fetching diagnostic settings for {subName} ({subProgress})...")
    for resource in tqdm(resources):
        try:
            diagnostic_settings = monitor_client.diagnostic_settings.list(resource.id)

            # add to list of diagnostic settings if workspace or setting name match
            matching_diagnostic_settings[resource.name] = [setting.as_dict() 
                                                      for setting in diagnostic_settings 
                                                      if setting.name == setting_name or 
                                                      (setting.workspace_id and setting.workspace_id.split("/")[-1] == workspace)]
        except Exception:
            matching_diagnostic_settings[resource.id] = []
    return matching_diagnostic_settings


def main():
    # Authenticate with Azure
    credential = get_credentials()
    
    # Parse args and subscription ids and throw error if neither -d or -w is used
    args = parse_args()

    if not (args.diagnostic or args.workspace):
        argparse.ArgumentParser().error("At least one of -d/--diagnostic or -w/--workspace is required.")

    subscription_ids = []
    with open(args.subscriptions, "r") as f:
        reader = csv.reader(f)
        for row in reader:
            subscription_ids.append(row)
    

    # Get all diagnostics for all resources in a subscription
    def get_subscription_diagnostics(subId, subName, subProgress):

        # Prepare diagnostics dictionary
        diagnostics = {}

        # Initialize clients
        resource_client = ResourceManagementClient(credential, subId)
        monitor_client = MonitorManagementClient(credential, subId)
        
        # Get all resources; return if no resources found
        all_resources = get_resources(resource_client, args.type)
        if not all_resources:
            return
        
        # Get all diagnostics settings for resourses
        diagnostics.update(get_diagnostic_settings(monitor_client, all_resources, subName, subProgress, args.diagnostic, args.workspace))

        return diagnostics


    # Print results
    def printResults(diagnostics):

        # Count for resources with logging enabled
        logging_enabled_ct = len(diagnostics)

        for resource, settings in diagnostics.items():
            print("\n" + resource.split("/")[-1])
            for setting in settings:
                print("\t" + setting["name"])
                for log in setting["logs"]:
                    category = log.get("category", log.get("category_group", None))
                    if category:
                        (prGreen if log["enabled"] else prRed)("\t\t" + category)
                    else:
                        print(log)
            if len(diagnostics[resource]) == 0:
                prRed("\tNO LOGGING ENABLED")
                logging_enabled_ct -= 1
        return logging_enabled_ct
    
    # Used to collect number of resources with logging enabled for each subscription
    logging_enabled_ct_per_sub = []


    # Print settings for each sub
    for sub in subscription_ids:
        diagnostics = get_subscription_diagnostics(sub[0], sub[1], (str(subscription_ids.index(sub)+1) + "/" + str(len(subscription_ids))))
        prYellow(f"\n----------------------------------------------------------\n{sub[1]}\n----------------------------------------------------------\n")
        if not diagnostics:
            prRed("No resources found.\n")
            logging_enabled_ct_per_sub.append([0, 0])
        else:
            logging_enabled_ct_per_sub.append([printResults(diagnostics), len(diagnostics)])


    # Print summary
    prYellow("\n----------------------------------------------------------\nSUMMARY\n----------------------------------------------------------\n")
    prYellow(f"Resources with logging enabled:")
    for index, sub in enumerate(subscription_ids):
        prYellow(f"\t{sub[1]}: {logging_enabled_ct_per_sub[index][0]}/{logging_enabled_ct_per_sub[index][1]}")
    prYellow("\n----------------------------------------------------------\n")


if __name__ == "__main__":
    main()
