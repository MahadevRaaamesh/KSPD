@echo off
cd /d "c:\Prithish S\KSPD"

echo Removing nested .git folder inside backend...
if exist "backend\.git" rmdir /s /q "backend\.git"

echo Unstaging submodule reference...
git rm --cached -r backend 2>nul

echo Staging all project files properly...
git add .

echo Committing...
git commit -m "feat: complete KSPD backend with analytics, map, graph, similarity search, copilot, and CI pipeline"

git branch -M main

echo Pushing to GitHub...
git push -u origin main --force

echo Done! Code pushed successfully to https://github.com/MahadevRaaamesh/KSPD.git
