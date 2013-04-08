import sys
import ast
import re
import os
import time
import calendar

# TODO:
# Blocking (More work on it)
# Show followers/friends (change api call because the current is problematic)
# Be able to go backwards in statuses/favs

# This twitter plugin can be extended even more. Just look at the twitter api
# doc here: https://dev.twitter.com/docs/api/1.1

# Thanks to ttytter for interface ideas!
# http://www.floodgap.com/software/ttytter/

# I've borrowed some ideas, functions for ainmosni and his twitter plugin
# https://github.com/ainmosni/weetwit

weechat_call = True
import_ok = True

try:
    import weechat
except:
    #import html parser so we can convert html strings to plain text
    import html.parser
    weechat_call = False

try:
    #Import python twitter lib
    from twitter import *
except:
    import_ok = False

# These two keys is what identifies this twitter client as "weechat twitter"
# If you want to change it you can register your own keys at:
# https://dev.twitter.com/apps/new

CONSUMER_SECRET = 'ivx3oxxkSOAOofRuhmGXQK4nkLFNXD94wbJiRUBhN1g'
CONSUMER_KEY = 'NVkYe8DAeaw6YRcjw662ZQ'

script_options = {
    "oauth_token" : "",
    "oauth_secret" : "",
    "verified" : "",
    "screen_name" : "",
    "last_id" : "",
    "print_id" : "on",
}

tweet_dict = {'cur_index': "a0"}

SCRIPT_NAME = "twitter"
SCRIPT_FILE_PATH = os.path.abspath(__file__)

twit_buf = ""
timer_hook = ""
home_counter = 0

html_escape_table = {
    '"': "&quot;",
    "'": "&apos;",
    }

def html_escape(text):
    """Produce entities within text."""
    return "".join(html_escape_table.get(c,c) for c in text)

def dict_tweet(tweet_id):
    cur_index = tweet_dict['cur_index']
    if not tweet_id in tweet_dict.values():
        if cur_index == 'z9':
            cur_index = 'a0'

        if cur_index[1] == '9':
            cur_index = chr(ord(cur_index[0]) + 1) + '0'
        else:
            cur_index = cur_index[0] + chr(ord(cur_index[1]) + 1)

        tweet_dict[cur_index] = tweet_id
        tweet_dict['cur_index'] = cur_index
        return cur_index
    else:
        for index, t_id in tweet_dict.items():
            if t_id == tweet_id:
                return index


def read_config():
    for item in script_options:
        script_options[item] = weechat.config_string(weechat.config_get("plugins.var.python."+SCRIPT_NAME+"." + item))

def config_cb(data, option, value):
    """Callback called when a script option is changed."""
    # for example, read all script options to script variables...
    # ...
    read_config()
    return weechat.WEECHAT_RC_OK

def add_to_nicklist(buf, nick):
    """Add nick to the nicklist."""
    weechat.nicklist_add_nick(buf, "", nick, 'bar_fg', '', '', 1)

def remove_from_nicklist(buf, nick):
    """Remove nick from the nicklist."""
    nick_ptr = weechat.nicklist_search_nick(buf, "", nick)
    weechat.nicklist_remove_nick(buf, nick_ptr)

def parse_for_nicks(text):
    #Parse text for twitter nicks and add them to nicklist
    regex = re.compile(r'@([A-Za-z0-9_]+)')
    reset = weechat.color('reset')
    for word in text.split():
        match = re.search(regex,word)
        if str(type(match)) == "<type '_sre.SRE_Match'>":
            nick = word[match.start(1):match.end(0)]
            buffer = twit_buf
            add_to_nicklist(buffer,nick)

def my_process_cb(data, command, rc, out, err):

    if rc == weechat.WEECHAT_HOOK_PROCESS_ERROR:
        weechat.prnt("", "Error with command '%s'" %
                command.replace(script_options["oauth_token"],"").replace(script_options["oauth_secret"],""))
        return weechat.WEECHAT_RC_OK

    if out != "":
        buffer = twit_buf
        if out[0] != "[" and out[0] != "{":
            #If message is just a string print it
            weechat.prnt(buffer, "%s%s" % (weechat.prefix("network"), out))
            return weechat.WEECHAT_RC_OK
        process_output = ast.literal_eval(out)
        #List message
        # TODO blocks returns more then 60
        if len(data) >= 1 and data[0] == "L":
            if len(process_output) > 60:
                t_id = dict_tweet(str(process_output[60])) + "\t"
                process_output = process_output[:60]
                end_mes = " ..."
            else:
                t_id = weechat.prefix("network")
                end_mes = ""

            for nick in process_output:
                add_to_nicklist(buffer,nick)
            weechat.prnt_date_tags(buffer, 0, "no_highlight",
                    "%s%s: %s%s" % (t_id, data[1:], process_output, end_mes))
            return weechat.WEECHAT_RC_OK

        if data == "About":
            weechat.prnt(buffer, "Nick: %s | Name: %s | Protected: %s" % (process_output['screen_name'],
                                                                        process_output['name'],
                                                                        process_output['protected']))
            weechat.prnt(buffer, "Description: %s" % process_output['description'])
            weechat.prnt(buffer, "Location: %s | Time zone: %s" % (process_output['location'], process_output['time_zone']))
            weechat.prnt(buffer, "Created at: %s | Verified user: %s" % (process_output['created_at'], process_output['verified']))
            weechat.prnt(buffer, "Following: %s | Followers: %s | Favourites: %s | Tweets: %s" % (process_output['friends_count'],
                                                                                               process_output['followers_count'],
                                                                                               process_output['favourites_count'],
                                                                                               process_output['statuses_count']))
            weechat.prnt(buffer, "Are you currently following this person: %s" % (process_output['following']))
            return weechat.WEECHAT_RC_OK

        cur_date = time.strftime("%Y-%m-%d", time.gmtime())

        for message in process_output:
            parse_for_nicks(message[3])
            nick = message[1]
            add_to_nicklist(buffer,nick)

            if script_options['print_id'] == 'on':
                t_id = weechat.color('reset') + ' ' + dict_tweet(message[2])
            else:
                t_id = ''

            mes_date = time.strftime("%Y-%m-%d", time.gmtime(message[0]))
            if cur_date != mes_date:
                cur_date = mes_date
                weechat.prnt(buffer, "\t\tDate: " + cur_date)

            weechat.prnt_date_tags(buffer, message[0], "notify_message",
                    "%s%s\t%s" % (nick, t_id, message[3]))
        if data == "id":
            try:
                script_options['last_id'] = process_output[-1][2]
                # Save last id
                weechat.config_set_plugin("last_id",script_options["last_id"])
            except:
                pass
        elif data != "":
            weechat.prnt(buffer, "%s%s" % (weechat.prefix("network"), data))
    if err != "":
        weechat.prnt("", "stderr: %s" % err)
    return weechat.WEECHAT_RC_OK

def get_twitter_data(cmd_args):
    # Read the oauth token and auth with the twitter api.
    # Return the requested tweets

    h = html.parser.HTMLParser()
    
    if len(cmd_args) < 3:
        return "Invalid command"

    oauth_token = cmd_args[1]
    oauth_secret= cmd_args[2]
    try:
        if cmd_args[3] == 'th':
            #use the old api to get the thread from a tweet
            #This is unoffical and might stop working at any moment
            twitter = Twitter(
                auth=OAuth(
                    oauth_token, oauth_secret, CONSUMER_KEY, CONSUMER_SECRET),
                secure=True,
                api_version='1',
                domain='api.twitter.com')
            tweet_data = twitter.related_results.show._(cmd_args[4])()
            #convert to new api data type
            new_data = []
            for data in tweet_data[0]['results']:
                new_data.append(data['value'])
    
            tweet_data = new_data
            tweet_data.reverse()
        else:
            twitter = Twitter(auth=OAuth(
            oauth_token, oauth_secret, CONSUMER_KEY, CONSUMER_SECRET))
    
            if cmd_args[3] == "u":
                kwargs = dict(count=20, screen_name=cmd_args[4])
                tweet_data = twitter.statuses.user_timeline(**kwargs)
            elif cmd_args[3] == "r":
                tweet_data = twitter.statuses.mentions_timeline()
            elif cmd_args[3] == "v":
                tweet_data = [twitter.statuses.show._(cmd_args[4])()]
            elif cmd_args[3] == "rt":
                tweet_data = [twitter.statuses.retweet._(cmd_args[4])()]
            elif cmd_args[3] == "d":
                #deletes tweet made by the user _(...) converts the id string to a call
                #returns the tweet that was deleted (not a list(dict) just a dict)
                #make it into a list so we don't have to write special cases for this
                tweet_data = [twitter.statuses.destroy._(cmd_args[4])()]
            elif cmd_args[3] == "t":
                #returns the tweet that was sent (not a list(dict) just a dict)
                #make it into a list so we don't have to write special cases for this
                tweet_data = [twitter.statuses.update(status=h.unescape(" ".join(cmd_args[4:])))]
            elif cmd_args[3] == "re":
                tweet_data = [twitter.statuses.update(status=h.unescape(" ".join(cmd_args[5:])),
                    in_reply_to_status_id=cmd_args[4])]
            elif cmd_args[3] == "new":
                tweet_data = twitter.statuses.home_timeline(since_id = cmd_args[4]) 
            elif cmd_args[3] == "follow":
                tweet_data = twitter.friendships.create(screen_name = cmd_args[4]) 
            elif cmd_args[3] == "unfollow":
                tweet_data = twitter.friendships.destroy(screen_name = cmd_args[4])
            elif cmd_args[0] == "settings":
                #this only gets called from within weechat
                return twitter.account.settings()
            elif cmd_args[3] == "f" or cmd_args[3] == "fo":
                if len(cmd_args) == 6:
                    kwargs = dict(screen_name = cmd_args[4], skip_status = True, cursor = int(cmd_args[5]))
                else:
                    kwargs = dict(screen_name = cmd_args[4], skip_status = True, cursor = -1)
                friend_list = list()
                num = 1
                #Get max 20*3 users
                while(kwargs['cursor'] != 0 and num <= 3):
                    if cmd_args[3] == "f":
                        tweet_data = twitter.friends.list(**kwargs)
                    else:
                        tweet_data = twitter.followers.list(**kwargs)
                    kwargs['cursor'] = tweet_data['next_cursor']
                    num += 1
                    for user in tweet_data['users']:
                        friend_list.append(user['screen_name'])
                if kwargs['cursor'] != 0:
                    friend_list.append(kwargs['cursor'])
                return friend_list
            elif cmd_args[3] == "a":
                return twitter.users.show(screen_name = cmd_args[4])
            elif cmd_args[3] == "b":
                tweet_data = twitter.blocks.create(screen_name = cmd_args[4]) 
            elif cmd_args[3] == "ub":
                tweet_data = twitter.blocks.destroy(screen_name = cmd_args[4]) 
            elif cmd_args[3] == "blocks":
                tweet_data = twitter.blocks.list(skip_status = True) 
                block_list = list()
                for user in tweet_data['users']:
                    block_list.append(users['screen_name'])
                return block_list
            elif cmd_args[3] == "fav":
                tweet_data = [twitter.favorites.create(id=cmd_args[4])]
            elif cmd_args[3] == "unfav":
                tweet_data = [twitter.favorites.destroy(id=cmd_args[4])]
            elif cmd_args[3] == "favs":
                if len(cmd_args) == 5:
                    tweet_data = twitter.favorites.list(screen_name=cmd_args[4])
                else:
                    tweet_data = twitter.favorites.list()
            elif cmd_args[3] == "limits":
                output = ""
                if len(cmd_args) >= 5:
                    tweet_data = twitter.application.rate_limit_status(resources=",".join(cmd_args[4:]))
                else:
                    tweet_data = twitter.application.rate_limit_status()
                for res in tweet_data['resources']:
                    output += res + ":\n"
                    for sub_res in tweet_data['resources'][res]:
                        output += "  " + sub_res[len(res)+2:] + ":\n"
                        output += "    " + 'reset' + ": " + time.strftime('%Y-%m-%d %H:%M:%S',
                                time.localtime(tweet_data['resources'][res][sub_res]['reset'])) + "\n"
                        output += "    " + 'limit' + ": " + str(tweet_data['resources'][res][sub_res]['limit']) + "\n"
                        output += "    " + 'remaining' + ": " + str(tweet_data['resources'][res][sub_res]['remaining']) + "\n"
                return output
            elif cmd_args[3] == "home":
                tweet_data = twitter.statuses.home_timeline()
            else:
                return "Invalid command: " + cmd_args[3]
    except:
        return "Invalid command: " + " ".join(cmd_args)
    # Because of the huge amount of data, we need to cut down on most of it because we only really want
    # a small subset of it. This also prevents the output buffer from overflowing when fetching many tweets
    # at once.
    output = []
    for message in tweet_data:
        output.append([calendar.timegm(time.strptime(message['created_at'],'%a %b %d %H:%M:%S +0000 %Y')),
            message['user']['screen_name'],
            message['id_str'],
            h.unescape(message['text'])])

    output.reverse()

    return output

# callback for data received in input
def buffer_input_cb(data, buffer, input_data):
    # ...
    global home_counter
    end_message = ""

    if input_data[0] == ':':
        if data != "silent":
            weechat.prnt_date_tags(buffer, 0, "no_highlight", input_data)
        input_args = input_data.split()
        command = input_args[0][1:]
        if command == 'd' and input_args[1] in tweet_dict:
            input_data = 'd ' + tweet_dict[input_args[1]]
            weechat.prnt(buffer, "%sYou deleted the following tweet:" % weechat.prefix("network"))
        elif command == 'v' and input_args[1] in tweet_dict:
            input_data = 'v ' + tweet_dict[input_args[1]]
        elif command == 'rt' and input_args[1] in tweet_dict:
            end_message = "id"
            input_data = 'rt ' + tweet_dict[input_args[1]]
        elif command == 're' and input_args[1] in tweet_dict:
            end_message = "id"
            input_data = 're ' + tweet_dict[input_args[1]] + input_data[6:]
        elif command == 'th' and input_args[1] in tweet_dict:
            weechat.prnt(buffer, "%sThread of the following tweet id: %s" % (weechat.prefix("network"), input_args[1]))
            input_data = 'th ' + tweet_dict[input_args[1]] + input_data[6:]
            end_message = "End of thread"
        elif command == 'new':
            end_message = "id"
            if script_options['last_id'] != "":
                input_data = 'new ' + script_options['last_id']
            else:
                input_data = 'home'
            if data != "silent":
                #Delay the home timeline update so we don't go over the api req limits
                home_counter += 1
                end_message = "Done"
        elif command == 'home':
            input_data = 'home'
            #Delay the home timeline update so we don't go over the api req limits
            home_counter += 1
            end_message = "Done"
        elif command == 'auth':
            if len(input_args) == 2:
                oauth_dance(buffer,input_args[1])
            else:
                oauth_dance(buffer)
        elif command == 'f' or command == 'fo':
            if len(input_args) == 3 and input_args[2] in tweet_dict:
                input_data = command + " " + input_args[1] + " " + tweet_dict[input_args[2]]
            elif len(input_args) == 2:
                if input_args[1] in tweet_dict:
                    input_data = command + " " + script_options['screen_name'] + " " + tweet_dict[input_args[1]]
                else:
                    input_data = input_data[1:]
            else:
                input_data = command + " " + script_options['screen_name']
            if command == 'f':
                #L because we are returning a list to be printed later on
                end_message = "LFollowing"
            else:
                end_message = "LFollowers"
        elif command == 'a':
            input_data = input_data[1:]
            end_message = "About"
        elif command == 'blocks':
            input_data = input_data[1:]
            end_message = "LBlock list"
        elif command == 'fav' and input_args[1] in tweet_dict:
            input_data = 'fav ' + tweet_dict[input_args[1]]
            weechat.prnt(buffer, "%sYou fave'd the following tweet:" % weechat.prefix("network"))
        elif command == 'unfav' and input_args[1] in tweet_dict:
            input_data = 'unfav ' + tweet_dict[input_args[1]]
            weechat.prnt(buffer, "%sYou unfave'd the following tweet:" % weechat.prefix("network"))
        else:
            input_data = input_data[1:]
            end_message = "Done"
    else:
        end_message = "id"
        #esacpe special chars when printing to commandline
        input_data = 't ' + "'" + html_escape(input_data) + "'"
        #input_data = 't ' + "'" + html.escape(input_data) + "'"

    weechat.hook_process("python3 " + SCRIPT_FILE_PATH + " " +
                script_options["oauth_token"] + " " + script_options["oauth_secret"] + " " +
                input_data, 10 * 1000, "my_process_cb", end_message)
    return weechat.WEECHAT_RC_OK

def my_command_cb(data, buffer, args):
    # ...

    buffer_input_cb(data, buffer, ":"+args)

    return weechat.WEECHAT_RC_OK

# TODO write help text
def hook_commands_and_completions():
    weechat.hook_command("twitter", "Command to interact with with twitter plugin",
        "[list] | [enable|disable|toggle [name]] | [add name plugin.buffer tags regex] | [del name|-all]",
        "description of arguments...",
        "list"
        " || enable %(filters_names)"
        " || disable %(filters_names)"
        " || toggle %(filters_names)"
        " || add %(filters_names) %(buffers_plugins_names)|*"
        " || del %(filters_names)|-all",
        "my_command_cb", "")

# callback called when buffer is closed
# TODO rewrite this so it unloads the plugin
def buffer_close_cb(data, buffer):
    # ...
    #TODO handle multiple buffers and free up global buffer pointers
    weechat.unhook_all()
    return weechat.WEECHAT_RC_OK

def timer_cb(data, remaining_calls):
    # ...
    #Get latest tweets from timeline
    global home_counter
    # Max 15 request for home timeline per 15min
    # If users req the home timeline delay the auto update
    if home_counter == 0:
        buffer_input_cb("silent", buffer, ":new")
    else:
        home_counter -= 1

    return weechat.WEECHAT_RC_OK

def tweet_length(message):
    """Replace URLs with placeholders, 20 for http URLs, 21 for https."""
    # regexes to match URLs
    octet = r'(?:2(?:[0-4]\d|5[0-5])|1\d\d|\d{1,2})'
    ip_addr = r'%s(?:\.%s){3}' % (octet, octet)
    # Base domain regex off RFC 1034 and 1738
    label = r'[0-9a-z][-0-9a-z]*[0-9a-z]?'
    domain = r'%s(?:\.%s)*\.[a-z][-0-9a-z]*[a-z]?' % (label, label)
    url_re = re.compile(r'(\w+://(?:%s|%s)(?::\d+)?(?:/[^\])>\s]*)?)' % \
            (domain, ip_addr), re.I)

    new_message = message

    for url in url_re.findall(message):
        short_url = 'x' * 20
        if url.startswith('https'):
            short_url = 'x' * 21
        new_message = new_message.replace(url, short_url)

    return len(new_message)

def my_modifier_cb(data, modifier, modifier_data, string):
    if weechat.current_buffer() != twit_buf:
        return string

    #check if this is a commandline argument
    if string == "" or string[0] == "/":
        return string

    length = tweet_length(string)
    
    # Subtract local command argument from length
    if string[:3] == ":re":
        #:re a2
        length = length - 6

    if length > 140:
        index = 140 - length
        string = string[:index] + weechat.color("*red") + string[index:]

    return string

def oauth_dance(buffer, pin = ""):
    #Auth the twitter client

    #Load to be able to open links in webbrowser
    import webbrowser
    global script_options

    if pin == "":
        weechat.prnt(buffer,"Hi there! We're gonna get you all set up to use this plugin.")
        twitter = Twitter(
            auth=OAuth('', '', CONSUMER_KEY, CONSUMER_SECRET),
            format='', api_version=None)
        oauth_token, oauth_token_secret = parse_oauth_tokens(
            twitter.oauth.request_token())
        weechat.prnt(buffer,"""
    In the web browser window that opens please choose to Allow
    access. Copy the PIN number that appears on the next page and type ":auth <pin>"
    in weechat. For example ":auth 123456"
    """)
        oauth_url = ('http://api.twitter.com/oauth/authorize?oauth_token=' +
                     oauth_token)
        weechat.prnt(buffer,"Opening: %s" % oauth_url)
    
        try:
            r = webbrowser.open(oauth_url)
            if not r:
                raise Exception()
        except:
            weechat.prnt(buffer,"""
    Uh, I couldn't open a browser on your computer. Please go here to get
    your PIN:
    
    """ + oauth_url)

        script_options['oauth_token'] = oauth_token
        script_options['oauth_secret'] = oauth_token_secret
    else:
        oauth_verifier = pin.strip()
        twitter = Twitter(
            auth=OAuth(
                script_options['oauth_token'], script_options['oauth_secret'],
                CONSUMER_KEY, CONSUMER_SECRET),
            format='', api_version=None)
        oauth_token, oauth_token_secret = parse_oauth_tokens(
            twitter.oauth.access_token(oauth_verifier=oauth_verifier))
        
        weechat.config_set_plugin('oauth_token', oauth_token)
        weechat.config_set_plugin('oauth_secret', oauth_token_secret)
        weechat.config_set_plugin('verified', 'yes')
        finish_init()

def parse_oauth_tokens(result):
    for r in result.split('&'):
        k, v = r.split('=')
        if k == 'oauth_token':
            oauth_token = v
        elif k == 'oauth_token_secret':
            oauth_token_secret = v
    return oauth_token, oauth_token_secret

def finish_init():
    global timer_hook

    buffer = twit_buf
    # timer called each minute when second is 00
    timer_hook = weechat.hook_timer(60 * 1000, 60, 0, "timer_cb", "")

    if script_options['screen_name'] == "":
        user_nick = get_twitter_data(['settings', script_options["oauth_token"], script_options["oauth_secret"]])['screen_name'] 
        weechat.config_set_plugin('screen_name', user_nick)
    else:
        user_nick = script_options['screen_name']

    weechat.buffer_set(buffer, "localvar_set_nick", user_nick)

    add_to_nicklist(buffer, user_nick)
    # Highlight user nick
    weechat.buffer_set(buffer, "highlight_words", user_nick)
    #Print friends
    buffer_input_cb("silent", buffer, ":f")
    #Get latest tweets from timeline
    buffer_input_cb("silent", buffer, ":new")

if __name__ == "__main__" and weechat_call:
    weechat.register( SCRIPT_NAME , "DarkDefender", "1.0", "GPL3", "Weechat twitter client", "close_cb", "")

    if not import_ok:
        weechat.prnt("", "Can't load the python twitter lib!")
        weechat.prnt("", "Install it via your package manager or go to http://mike.verdone.ca/twitter/")
    else:
        hook_commands_and_completions()

        # Set register script options if not available

        for option, default_value in script_options.items():
            if not weechat.config_is_set_plugin(option):
                weechat.config_set_plugin(option, default_value) 

        read_config()
        # hook for config changes
        
        weechat.hook_config("plugins.var.python." + SCRIPT_NAME + ".*", "config_cb", "")

        # create buffer
        twit_buf = weechat.buffer_new("twitter", "buffer_input_cb", "", "buffer_close_cb", "")
        
        # set title
        weechat.buffer_set(twit_buf, "title", "Twitter buffer, type ':help' for options.")
        
        # disable logging, by setting local variable "no_log" to "1"
        weechat.buffer_set(twit_buf, "localvar_set_no_log", "1")

        #show nicklist
        weechat.buffer_set(twit_buf, "nicklist", "1")

        #newline autocomplete
        weechat.nicklist_add_nick(twit_buf, "", "&#13;&#10;", 'bar_fg', '', '', 1)

        #Hook text input so we can update the bar item
        weechat.hook_modifier("input_text_display", "my_modifier_cb", "")

        if script_options['verified'] == 'yes':
            finish_init()
        else:
            weechat.prnt(twit_buf,"""You have to register this plugin with twitter for it to work.
Type ":auth" and follow the instructions to do that""")
            weechat.prnt(twit_buf,"Weechat might freeze for short periods of time during this setup.")

elif import_ok: 
    print(get_twitter_data(sys.argv))
else:
    print("Can't load twitter python lib")

