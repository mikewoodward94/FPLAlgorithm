An algorithm that attempts to produce optimal FPL team based purely on FPL points scored.

You will need to enter your FPL Team ID, which can be found in the url of your fpl teams gameweek history, in FPLgorithm.py
You will also need to enter your FPL League ID, which can be found in the url of your league, in FPLgraph.py

Then you should be able to run FPLgorithm.py and it'll produce some lovely graphs and an excel workbook with your optimal team.

Annoyingly there is no historical flag (injury) data in the FPL API so you'll need to have a version of 'flagged_players.csv' in your Data folder. I've included a limited version of this, as it's all I have. It can be updated by running  FPLflagged.py, ideally you'd do this daily but that's just silly I know so good luck. You could run it on pythonanywhere.com or something similar which is a good idea actually I'll do that.

Set transfers to be 15 to simulate a wildcard.
Only really works properly when done after all games of gameweek finished before next gameweek starts, it's a limitation but not the end of the world, but just be aware.

Top 10k FPL Overall Rank not guaranteed.
