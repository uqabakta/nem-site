Correct Workflow to edit files/codes:

1. Open GitHub Desktop, select the repo you need (nem-site for this analytics change).
2. Pull origin first.
3. Edit the file in C:\dev\nem-site directly.
4. Commit + Push.
5. For nem-site → GitHub Actions rebuilds the live site. For NEM_Dashboards → the server picks it up on its next 6-hourly run.