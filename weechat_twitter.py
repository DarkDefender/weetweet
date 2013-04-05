import sys
import ast
import re
import os

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

add_last_id = False
twit_buf = ""
timer_hook = ""


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

# TODO this only adds nicks so that the colorize plugin colors it instead
# So this doesn't have to return text anymore
def colorize_twit(text):
    regex = re.compile(r'@([A-Za-z0-9_]+)')
    reset = weechat.color('reset')
    for word in text.split():
        match = re.search(regex,word)
        if str(type(match)) == "<type '_sre.SRE_Match'>":
            nick = word[match.start(1):match.end(0)]
            buffer = twit_buf
            add_to_nicklist(buffer,nick)
            #nick_color = weechat.info_get('irc_nick_color', nick)
            #new_word = word.replace(nick, '%s%s%s' % (nick_color,nick,reset))
            #text = text.replace(word,new_word)
    return text

def my_process_cb(data, command, rc, out, err):
    process_output = list()
    global add_last_id
    if out != "":
        process_output = ast.literal_eval(out)
    if int(rc) >= 0:
        buffer = twit_buf
        for message in process_output:
            message['text'] = colorize_twit(message['text'])
            nick = message['user']['screen_name']
            add_to_nicklist(buffer,nick)

            if script_options['print_id'] == 'on':
                t_id = weechat.color('reset') + ' ' + dict_tweet(message['id_str'])
            else:
                t_id = ''

            weechat.prnt_date_tags(buffer, 0, "notify_message",
                    "%s%s\t%s" % (nick, t_id, message['text']))
        if add_last_id == True:
            add_last_id = False
            if process_output != []:
                script_options['last_id'] = process_output[-1]['id_str']

        if data != "":
            weechat.prnt(buffer, "%s%s" % (weechat.prefix("network"), data))

    return weechat.WEECHAT_RC_OK

def get_twitter_data(cmd_args):
    # Read the oauth token and auth with the twitter api.
    # Return the requested tweets

    h = html.parser.HTMLParser()
    
    if len(cmd_args) < 2:
        return "invalid command"

    oauth_token = cmd_args[1]
    oauth_secret= cmd_args[2]

    if len(cmd_args) == 5 and cmd_args[3] == 'th':
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

        if len(cmd_args) == 5 and cmd_args[3] == "u" and cmd_args[4]:
            kwargs = dict(count=20, screen_name=cmd_args[4])
            tweet_data = twitter.statuses.user_timeline(**kwargs)
        elif len(cmd_args) == 4 and cmd_args[3] == "r":
            tweet_data = twitter.statuses.mentions_timeline()
        elif len(cmd_args) == 5 and cmd_args[3] == "v":
            tweet_data = [twitter.statuses.show._(cmd_args[4])()]
        elif len(cmd_args) == 5 and cmd_args[3] == "rt":
            tweet_data = [twitter.statuses.retweet._(cmd_args[4])()]
        elif len(cmd_args) == 5 and cmd_args[3] == "d":
            #deletes tweet made by the user _(...) converts the id string to a call
            #returns the tweet that was deleted (not a list(dict) just a dict)
            #make it into a list so we don't have to write special cases for this
            tweet_data = [twitter.statuses.destroy._(cmd_args[4])()]
        elif len(cmd_args) >= 5 and cmd_args[3] == "t":
            #returns the tweet that was sent (not a list(dict) just a dict)
            #make it into a list so we don't have to write special cases for this
            tweet_data = [twitter.statuses.update(status=h.unescape(" ".join(cmd_args[4:])))]
        elif len(cmd_args) >= 6 and cmd_args[3] == "re":
            tweet_data = [twitter.statuses.update(status=h.unescape(" ".join(cmd_args[5:])),
                in_reply_to_status_id=cmd_args[4])]
        elif len(cmd_args) == 5 and cmd_args[3] == "new":
            tweet_data = twitter.statuses.home_timeline(since_id = cmd_args[4]) 
        elif len(cmd_args) == 5 and cmd_args[3] == "follow":
            tweet_data = twitter.friendships.create(screen_name = cmd_args[4]) 
        elif len(cmd_args) == 5 and cmd_args[3] == "unfollow":
            tweet_data = twitter.friendships.destroy(screen_name = cmd_args[4])
        elif len(cmd_args) == 3 and cmd_args[0] == "settings":
            #this only gets called from within weechat
            return twitter.account.settings()
        else:
            tweet_data = twitter.statuses.home_timeline()

    # Because of the huge amount of data, we need to cut down on most of it because we only really want
    # a small subset of it. This also prevents the output buffer from overflowing when fetching many tweets
    # at once.
    output = []
    for message in tweet_data:
        output.append({'user': {'screen_name': message['user']['screen_name']},
            'text': h.unescape(message['text']),
            'id_str': message['id_str']})

    output.reverse()

    return output

# callback for data received in input
def buffer_input_cb(data, buffer, input_data):
    # ...
    global add_last_id
    end_message = ""

    if input_data[0] == ':':
        if data != "silent":
            weechat.prnt(buffer, input_data)
        input_args = input_data.split()
        if input_args[0][1:] == 'd' and input_args[1] in tweet_dict:
            input_data = 'd ' + tweet_dict[input_args[1]]
            weechat.prnt(buffer, "%sYou deleted the following tweet:" % weechat.prefix("network"))
        elif input_args[0][1:] == 'v' and input_args[1] in tweet_dict:
            input_data = 'v ' + tweet_dict[input_args[1]]
        elif input_args[0][1:] == 'rt' and input_args[1] in tweet_dict:
            add_last_id = True
            input_data = 'rt ' + tweet_dict[input_args[1]]
        elif input_args[0][1:] == 're' and input_args[1] in tweet_dict:
            add_last_id = True
            input_data = 're ' + tweet_dict[input_args[1]] + input_data[6:]
        elif input_args[0][1:] == 'th' and input_args[1] in tweet_dict:
            weechat.prnt(buffer, "%sThread of the following tweet id: %s" % (weechat.prefix("network"), input_args[1]))
            input_data = 'th ' + tweet_dict[input_args[1]] + input_data[6:]
            end_message = "End of thread"
        elif input_args[0][1:] == 'new':
            add_last_id = True
            if script_options['last_id'] != "":
                input_data = 'new ' + script_options['last_id']
            else:
                input_data = 'update'
        elif input_args[0][1:] == 'auth':
            if len(input_args) == 2:
                oauth_dance(buffer,input_args[1])
            else:
                oauth_dance(buffer)
        else:
            input_data = input_data[1:]
            end_message = "Done"
    else:
        add_last_id = True
        #esacpe special chars when printing to commandline
        input_data = 't ' + "'" + html_escape(input_data) + "'"
        #input_data = 't ' + html.escape(input_data)

    weechat.hook_process("python3 " + SCRIPT_FILE_PATH + " " +
                script_options["oauth_token"] + " " + script_options["oauth_secret"] + " " +
                input_data, 10 * 1000, "my_process_cb", end_message)
    return weechat.WEECHAT_RC_OK

def my_command_cb(data, buffer, args):
    # ...

    buffer_input_cb(data, buffer, ":"+args)

    return weechat.WEECHAT_RC_OK

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
    # Save last id
    weechat.config_set_plugin("last_id",script_options["last_id"])
    
    #TODO handle multiple buffers and free up global buffer pointers
    weechat.unhook_all()
    return weechat.WEECHAT_RC_OK

def close_cb():
    weechat.config_set_plugin("last_id",script_options["last_id"])
    return weechat.WEECHAT_RC_OK

def timer_cb(data, remaining_calls):
    # ...
    #Get latest tweets from timeline
    buffer_input_cb("silent", buffer, ":new")

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
    #TODO don't count commandline arguments
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
        weechat.prnt(buffer,"Weechat might freeze for short periods of time during this setup.")
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

elif import_ok: 
    print(get_twitter_data(sys.argv))
else:
    print("Can't load twitter python lib")

