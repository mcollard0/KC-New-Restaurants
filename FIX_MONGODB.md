# Fix MongoDB Connection

## The Problem
The MongoDB connection is failing with `[SSL: TLSV1_ALERT_INTERNAL_ERROR]`.
This indicates that the **MongoDB Atlas server is rejecting the connection**, likely due to:
1. **IP Whitelist Restriction**: The current IP address is not allowed to connect.
2. **Paused Cluster**: If this is a free Tier (M0) cluster, it may have been paused due to inactivity.

## Solution

### 1. Check if Cluster is Paused
1. Log in to [MongoDB Atlas](https://cloud.mongodb.com).
2. Check if your cluster is marked as **"Paused"**.
3. If so, click **"Resume"**.

### 2. Add Current IP to Whitelist
1. Go to **Network Access** in the Atlas sidebar.
2. Click **"Add IP Address"**.
3. Add the following IP address:
   **`136.33.18.34`**
   (or click "Add Current IP Address" if you are running this locally)
4. Save and wait 1-2 minutes.

## Verification
Run the database status check:
```bash
python3 database_status_check.py
```
Or run the application in dry-run mode:
```bash
python3 "KC New Restaurants.py" --dry-run
```
