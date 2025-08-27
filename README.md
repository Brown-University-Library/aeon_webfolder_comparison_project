# About

This is an experimental project to compare Aeon webfolders.

The challenge we have is that we have an existing Aeon webfolder ("old_folder") that has customizations. And we have a new Aeon webfolder ("new_folder") that upgrades various html, css, and js files.

The goal is to update the existing webfolder with the new files, while preserving the customizations.

This repo will contain code for:
- Comparing the two webfolders, producing json indicating files that are different.
- Given a pair of files ("old" and "new"), looking at each diff "hunk", and attempting to determine if the hunk is a customization or an upgrade, or a mix. It will output json indicating a probability that the hunk is a customization or an upgrade, or a mix.
- Running the file-pair comparison in a loop, and outputting json indicating a probability that each file is a customization or an upgrade, or a mix.

---
