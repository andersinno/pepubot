PePuBot
=======

PePuBot is a Slack bot that can arrange Friday bottle lotteries on a
Slack channel with a specific set of rules.

The Name
--------

PePu comes from Finnish words "Perjantai Pullo", which means "Friday
Bottle".  Bot is shortened from Robot, as you may know. ;-)

The Rules
---------

* PePu is arranged in rounds, usually a round is arranged on every
  Friday, but it's also possible to arrange a round on any other day
  or to skip rounds.

* When a PePu round is running in a channel anyone in the channel can
  attend and get a new ticket to the lottery box by posting a funny
  picture or video to the channel.

* Each attendee may get at most one new ticket to the lottery box per a
  PePu round.  If the same person posts several pictures or videos to
  the PePu channel, only the first one is awarded with a ticket.

* When the round is ended, the winner will be selected by randomly
  picking one of the tickets from the lottery box.  Then all tickets of
  the winner will be removed from the lottery box and the rest of the
  tickets will be stored for the next PePu round.  I.e. your chances to
  win increase on every round until you win.

* Anyone can arrange a PePu round, but the person who starts the round
  should also arrange the prize bottle.

* The person who starts the round also decides when the round ends and
  is responsible to do so before the day ends.

Requirements
------------

To run PePuBot you need Python 3.7 and a Slack account.

Installing
----------

1. Add a new app to Slack in https://api.slack.com/apps and add a bot
   for that app.

2. Enable the following permissions for the app:

   * bot

     - To act as a bot user in Slack

   * chat:write:bot

     - For writing to the channel

   * reactions:write

     - For marking ticket additions with reactions to the picture or
       video message.

   * users:read

     - For filling user names to the tickets

3. Install PePuBot and its dependencies to a Python virtual environment
   or to a Docker container or using whatever isolation you prefer.  You
   may do this with a command like::

     pip install .

4. Copy the "Bot User OAuth Access Token" value to environment variable
   named ``SLACK_API_TOKEN`` or to a line in a configuration file named
   ``pepubot.conf``.  There is a ``pepubot.conf.template`` which you can
   use as a base.

   - Note: Each configuration option can be set in the configuration
     file or with an environment variable with the same name.  If a
     variable is defined in both places, the value will be read from the
     environment.

5. Start the PePuBot with the script installed by Pip::

     pepubot

   By default the configuration file will be read from the current
   working directory by name ``pepubot.conf``, but alternative location
   can be given via command line argument::

     pepubot --config-file /path/to/pepubot.conf
