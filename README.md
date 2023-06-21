# README

`mountains.json` is dump of all the mountains and the routes up them from
https://climbnz.org.nz and is used by https://topos.nz to provide route
information.

The data is automatically updated once a week, on Mondays. All the mountains
from https://climbnz.org.nz/mountains are included.

## Running Locally

```bash
git clone https://github.com/fallaciousreasoning/nz-mountains.git
cd nz-mountains

python install -r requirements.txt

# This may take some time...
python mountains.py
```

Output is in `mountains.json` 

## Attribution

All data comes from [https://climbnz.org.nz/nz](ClimbNZ) licensed per [https://creativecommons.org/licenses/by-nc-sa/3.0/nz/](Creative Commons CC BY-NC-SA 3.0 NZ)
