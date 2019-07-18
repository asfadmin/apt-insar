Setting development environment
======================================

Install docker on your machine

Pull the latest image:

```
docker pull asfdaac/apt-insar
```

Run docker container in interactive mode:
```
docker run -it --entrypoint /bin/bash asfdaac/apt-insar
```

Develop inside the container:
```
run insar.py to test code changes inside the container
```

Git apt-insar best practices
=======================

Commit message
--------------

Begin commits the name of the issue being fixed, a short description and a reference to a issue number.

```
No product for zip #61

Fixes an issue where no products are being found to zip.
```

Initiate your fork
-----------------------------

Fork asfadm/apt-insar from github, and then
```
git clone https://github.com/asfadm/apt-insar
cd apt-insar
git remote add my_user_name https://github.com/my_user_name/apt-insar.git
```

Updating against upstream
--------------------------------------------------

```
git checkout master
git fetch origin
git reset --hard origin/master
```

Working with a feature branch
-----------------------------

```
git checkout master
git checkout -b my_new_feature_branch

# Make changes and then commit them:
< work happens here >
git commit -a 

# you may need to fetch from master if you need changes added since branch creation
git fetch origin
git rebase origin/master

# At end of your work, make sure history is reasonable by folding non
# significant commits into a consistent set
git rebase -i master (use 'fixup' for example to merge several commits together,
and 'reword' to modify commit messages)

# or alternatively, in case there is a big number of commits and marking
# all them as 'fixup' is tedious
git fetch origin
git rebase origin/master
git reset --soft origin/master
git commit -a -m "Put here the synthetic commit message"

# push your branch
git push my_user_name my_new_feature_branch
From GitHub, issue a pull request
```


Please do NOT
------------------------
Change any commit or history of anything in the repo.


