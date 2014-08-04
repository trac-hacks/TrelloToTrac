TrelloToTrac
==========

Trac Plugin for Trello Integration
Converts cards to a board trello and as part of trac tickets.
Ticktes are associated with a release and a iteretion (AgileTrac).


    $ sudo pip install py-trello
    $ sudo pip install trolly


### Get oauth token
    sudo pip install httplib2
    sudo pip install oauth2
    sudo pip install configparser

set config.ini  with this content
https://trello.com/1/appKey/generate

    #config.ini
    [trello]
    consumer_key = **
    consumer_secret = **

    #run
    python util.py

Set oauth_token result in trac.ini

    user_auth_token = **

Add to trac.ini consumer_key as

    api_key = ***

Add to trac.ini agiletrac if agiletracplugin is active as

    agile_trac = false/true

Add to trac.ini estimationtools if estimationtools is active as

    estimationtools = false/true
You can insert estimationtools field value with this format in card name.
(VALUE) nameofcard

Add to trac.ini "trellocard" custom field

    trellocard = select
    trellocard.label = Trello Card
    trellocard.value = 0

Final trac.ini

    [trello]
    api_key = ***
    user_auth_token = ***
    boards = ***  [boards comma separated]
    lists = ***  [lists comma separeted]
    agile_trac = false/true
    estimationtools = false/true

    [trello-user]
    5****f = magni

    [ticket-custom]
    trellocard = select
    trellocard.label = Trello Card
    trellocard.value = 0
