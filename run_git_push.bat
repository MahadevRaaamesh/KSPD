@echo off
cd /d "c:\Prithish S\KSPD"
echo Initializing Git...
git init
git config user.email "mahadevramesh@example.com"
git config user.name "MahadevRaaamesh"
git remote remove origin
git remote add origin https://github.com/MahadevRaaamesh/KSPD.git
echo Staging files...
git add .
echo Committing...
git commit -m "feat: complete KSPD backend with analytics, map, graph, similarity search, copilot, and CI pipeline"
git branch -M main
echo Pushing to GitHub...
git push -u origin main
echo Done.
