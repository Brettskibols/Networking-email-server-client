import selectors
import queue
import traceback
import SMTPServerEncryption
import time
from threading import Thread

serverLibDebugger = True  # Debugging script to assist with building and testing toggle for more output info


class Module(Thread):
    def __init__(self, sock, addr):
        Thread.__init__(self)

        self._selector = selectors.DefaultSelector()
        self._sock = sock
        self._addr = addr
        self._listofrecipients = []  # Storage within the class for thread, without this list gets wiped every time
        self._helocompleted = False  # Bool for if helo has been completed, enables mail to start
        self._mailcompleted = False  # Bool for if mail complete enables RCPT to start
        self._rcptcompleted = False  # Bool for recipients completed enables DATA to be started
        self._serverstate = "default"  # State machine for server, dictates which commands are reachable
        self._mailsender = ""  # MAIL FROM: buffer
        self._datareadbuffer = ""  # Houses all the read data for writing to txt files
        self._currenttime = ""  # Going to be used to store the current time for writing to text files
        self._alldataread = False  # Obsolete field, kept for use in username reading
        self._incoming_buffer = queue.Queue()
        self._outgoing_buffer = queue.Queue()

        self.encryption = SMTPServerEncryption.nws_encryption()
        # Sets encryption to specified in SMTPServerEncryption

        events = selectors.EVENT_READ | selectors.EVENT_WRITE
        self._selector.register(self._sock, events, data=None)

    def run(self):
        try:
            while True:
                events = self._selector.select(timeout=None)
                for key, mask in events:
                    try:
                        if mask & selectors.EVENT_READ:
                            self._read()
                        if mask & selectors.EVENT_WRITE and not self._outgoing_buffer.empty():
                            self._write()
                    except Exception:
                        print(
                            "main: error: exception for",
                            f"{self._addr}:\n{traceback.format_exc()}",
                        )
                        self._sock.close()
                if not self._selector.get_map():
                    break
        except KeyboardInterrupt:
            print("caught keyboard interrupt, exiting")
        finally:
            self._selector.close()

    def _read(self):
        # Reads incoming messages and either decrypts incoming buffer or errors out
        try:
            data = self._sock.recv(4096)
        except BlockingIOError:
            print("blocked")
            # Resource temporarily unavailable (errno EWOULDBLOCK)
            pass
        else:
            if data:
                self._incoming_buffer.put(self.encryption.decrypt(data.decode()))
            else:
                raise RuntimeError("Peer closed.")

        self._process_response()

    def _write(self):
        try:
            message = self._outgoing_buffer.get_nowait()
        except:
            message = None

        if message:
            print("sending", repr(message), "to", self._addr)
            # Prints sending message to console
            try:
                sent = self._sock.send(message)
            except BlockingIOError:
                # Resource temporarily unavailable (errno EWOULDBLOCK)
                pass

    def _create_message(self, content):
        encoded = self.encryption.encrypt(content)
        # Encrypts outgoing message if encryption selected
        nwencoded = encoded.encode()
        self._outgoing_buffer.put(nwencoded)
        # Adds newly encoded message to the outgoing buffer

    def _process_response(self):
        # Splits incoming message into command and message
        message = self._incoming_buffer.get()
        header_length = 4
        if self._serverstate != "DATA_serverstate":
            if len(message) >= header_length:
                self._module_processor(message[0:header_length], message[header_length:])
        else:
            self._process_for_text_file(message, self._mailsender, self._listofrecipients, self._datareadbuffer)

    def _process_for_text_file(self, message, _mailsender, _listofrecipients, _datareadbuffer):
        # Reads buffer data string and writes to a local text file
        if self._datareadbuffer == "":
            self._create_message("Confirming Data collection started please type, enter '.' to stop")
        if message != '.':
            self._datareadbuffer = self._datareadbuffer + "\r \n" + message
        else:
            print("Finished adding message to the buffer")
            timeformatforfxtfile = ""
            ts = time.gmtime()
            self._currenttime = (time.strftime("%c", ts))
            timeformatforfxtfile = self._currenttime.replace(":", "-")
            print("The current time is = " + timeformatforfxtfile)

            # Code for popping all the TO, FROM and DATA into a text doc in current folder
            # Unique time at the start of the text file will create a new doc every time persistently stored

            my_file_handle = open(timeformatforfxtfile + ".txt", "w")
            my_file_handle.write("FROM: " + _mailsender + "\n")

            # Need to convert list to string using join function
            recipientsstring = ""
            recipientsstring = ', '.join(_listofrecipients)
            my_file_handle.write("TO: " + recipientsstring + "\n")
            my_file_handle.write("\n")
            my_file_handle.write(_datareadbuffer)
            my_file_handle.close()

            self._serverstate = "default"
            self._mailcompleted = False
            self._rcptcompleted = False

    def _module_processor(self, command, message):  # Sets response to incoming command and message
        uppercommand = command.upper()

        if 'HELO' in uppercommand[0:4]:
            # Used to check is domain is valid
            self._serverstate = "HELO_serverstate"
            self._helocompleted = True
            if self._serverstate == "HELO_serverstate":
                self._create_message("250 OK " + (str(self._addr)).split(', ')[0] + ")")  # splits domain so readable
                print("Hello from: ", self._addr)
                if serverLibDebugger:
                    print("Original command = " + command)
                    print("Upper command = " + uppercommand)
                print("Hello from: ", self._addr)

        # Unreachable error codes for future use in HELO
        # self._create_message("501 Syntax error in parameters or arguments")
        # self._create_message("504 Command parameter not implemented")
        # self._create_message("421 <domain> Service not available,closing transmission channel")

        elif 'NOOP' in uppercommand[0:4]:
            # Checks to see if connected server is still there
            self._serverstate = "NOOP_serverstate"
            if self._serverstate == "NOOP_serverstate":
                self._create_message("250 OK")
                print("Received a NOOP")

        # Unreachable error codes for future use in NOOP
        # self._create_message("421 <domain> Service not available,closing transmission channel")

        elif 'HELP' in uppercommand[0:4]:
            # Will give the user the RDC link to look up commands, commands given in test doc provided
            self._serverstate = "HELP_serverstate"
            if self._serverstate == "HELP_serverstate":
                self._create_message(f"214 Help message, for further help please visit "
                                     f"https://tools.ietf.org/html/rfc821")
                print("Received a HELP")

        # Unreachable error codes for future use in HELP
        # self._create_message("501 Syntax error in parameters or arguments")
        # self._create_message("502 Command not implemented")
        # self._create_message("504 Command parameter not implemented")
        # self._create_message("421 <domain> Service not available,closing transmission channel")

        elif 'RSET' in uppercommand[0:4]:
            self._serverstate = "MAIL_serverstate"
            # Resetting the RCPT, MAIL and DATA strings so data is not kept when initiating new mails.
            self._mailsender = ""
            self._listofrecipients = []
            self._datareadbuffer = ""
            self._currenttime = ""
            print("Received a reset command, reset mail data")
            self._create_message("250 OK")
            self._serverstate = "default"
            self._helocompleted = False
            self._mailcompleted = False
            self._rcptcompleted = False

        # Unreachable error codes for future use in RSET
        # self._create_message("501 Syntax error in parameters or arguments")
        # self._create_message("504 Command parameter not implemented")
        # self._create_message("421 <domain> Service not available,closing transmission channel")

        elif 'MAIL' in uppercommand[0:4]:
            # Initiates the mail loop to send a mail message
            self._serverstate = "MAIL_serverstate"
            # Resetting the RCPT, MAIL and DATA strings so data is not kept when initiating new mails.
            self._mailsender = ""
            self._listofrecipients = []
            self._datareadbuffer = ""
            self._currenttime = ""
            if not self._helocompleted:
                self._create_message("503 Bad sequence of commands")
                return

            if ' FROM:' in message[0:7]:
                # Splits message from 'FROM: sender' so it can be stored for mail message
                self._mailsender = message.split(':')[1]
            else:
                self._create_message("500 Syntax error, command unrecognized ")
                return
            if self._serverstate == "MAIL_serverstate":
                self._create_message("250 OK")
                self._mailcompleted = True
                print("Received a MAIL")
                if serverLibDebugger:
                    print("This command will now save the name of the address of the SENDER")
                    print("Mail Sender Stored as = " + self._mailsender)
                    print("The original message was = " + message)
                    # Some debugging text to dev can see the output of mail as well as original message

        # Unreachable error codes for future use in MAIL
        # self._create_message("501 Syntax error in parameters or arguments")
        # self._create_message("421 <domain> Service not available,closing transmission channel")
        # self._create_message("552 Requested mail action aborted: exceeded storage allocation")
        # self._create_message("451 Requested action aborted: local error in processing")
        # self._create_message("452 Requested action not taken: insufficient system storage")

        elif 'RCPT' in uppercommand[0:4]:
            if not self._mailcompleted:
                self._create_message("503 Bad sequence of commands")
                return
            self._serverstate = "RCPT_serverstate"
            if ' TO:' in message[0:5]:
                splitmessage = (message.split(':')[1])
            else:
                self._create_message("500 Syntax error, command unrecognized ")
                return
            self._listofrecipients.append(splitmessage)

            # Add this recipients to the 'listofrecipients' possibly adding a ' ,' in between for clarity?

            if self._serverstate == "RCPT_serverstate":
                self._create_message("250 OK")
                self._rcptcompleted = True
                print("Received a RCPT which was then stored")
                if serverLibDebugger:
                    print("This command will now store the forward path, if path unknown return 550 failure")
                    print("The full list of recipients as now as follows = ")

                    print(self._listofrecipients)
                    # RCPT Can be repeated any number of times

        # Unreachable error codes for future use in RCPT
        # self._create_message("501 Syntax error in parameters or arguments")
        # self._create_message("421 <domain> Service not available,closing transmission channel")
        # self._create_message("550 Requested action not taken")
        # self._create_message("551 User not local; please try <forward-path> ")
        # self._create_message("552 Requested mail action aborted: exceeded storage allocation")
        # self._create_message("553 Requested action not taken: mailbox name not allowed  ")
        # self._create_message("450 Requested mail action not taken: mailbox unavailable ")
        # self._create_message("451 Requested action aborted: local error in processing")
        # self._create_message("452 Requested action not taken: insufficient system storage")

        elif 'DATA' in uppercommand[0:4]:
            if not self._rcptcompleted:
                self._create_message("503 Bad sequence of commands")
                return
            self._serverstate = "DATA_serverstate"
            self._create_message("354 Intermediate")
            self._process_for_text_file(message, self._mailsender, self._listofrecipients, self._datareadbuffer)
            # if serverLibDebugger:
            # print("Returns 354 Intermediate code and considers all succeeding lines message text")

        # Unreachable error codes for future use in DATA
        # self._create_message("501 Syntax error in parameters or arguments")
        # self._create_message("421 <domain> Service not available,closing transmission channel")
        # self._create_message("552 Requested mail action aborted: exceeded storage allocation")
        # self._create_message("554 Transaction failed")
        # self._create_message("451 Requested action aborted: local error in processing")
        # self._create_message("452 Requested action not taken: insufficient system storage")

        elif 'QUIT' in uppercommand[0:4]:
            self._listofrecipients = []  # Returning buffers to null value good practice
            self._mailsender = ""  # ""
            self._datareadbuffer = ""  # ""
            self._currenttime = ""  # ""
            self.close()

        else:
            self._create_message("500 Syntax error, command unrecognized ")
            print("Received an unknown command")
            if serverLibDebugger:
                print("Original command = " + uppercommand)
                print("Uppercommand = " + uppercommand)
                print("Shortened command is = " + command[0:4])
                print("Shortened SupperCommand = " + command[0:4])
                print("Original message was = " + message)
                print("Shortened message was shortened to = " + message[5:10])

    def close(self):
        print("closing connection to", self._addr)
        try:
            self._selector.unregister(self._sock)
        except Exception as e:
            print(
                f"error: selector.unregister() exception for",
                f"{self._addr}: {repr(e)}",
            )
        try:
            self._sock.close()
        except OSError as e:
            print(
                f"error: socket.close() exception for",
                f"{self._addr}: {repr(e)}",
            )
        finally:
            # Delete reference to socket object for garbage collection
            self._sock = None
#  TODO: Hash lib import for salting and hashing
