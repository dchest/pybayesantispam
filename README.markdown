PyBayesAntispam
===============

Simple Bayesian spam rating in Python that is easy to use, small, contained in a single file, and doesn't require any external modules.

Author: Dmitry Chestnykh, [Coding Robots](http://www.codingrobots.com)

License: MIT (see bayes.py)


Example usage
-------------

### Creating and destroying Storage and Bayes objects

With data output to file "bayes.dat":

	import bayes
	
	storage = bayes.Storage("bayes.dat", 10)
	try:
	    storage.load()
	except IOError:
	    pass  # don't fail if bayes.dat doesn't exist, it will be created

	bayes = bayes.Bayes(storage)

Train and/or check for spam (described below). After you're done (e.g. before exiting from script) call:
	
	storage.finish()
	
to save changes (they'll be saved only if needed).

#### Explanation

First, you create a *Storage* object with the following arguments:
		
*filename* 

Path to data file where probabilities of tokens are stored.

*min_save_count* (default 5)

How many trainings should be performed before saving data to file. This is needed purely for performance reasons. Since probability data can contain hundreds of thousands tokens (saving half a million tokens takes a few seconds on my MacBook Air), it would be unwise to save this data after every train operation. If you set *min_save_count* to 10, data will be written out to file every 10 train operations.

Next, you create a *Bayes* object with your *Storage* object as argument. The separation of storage is here to improve performance of web applications (and to enable using of other storages). For example, if you create your storage before interacting with FastCGI server, and share it with all *Bayes* instances, your web app will only load data on startup, not on every visit of a page. **Note, however, that currently *Storage* is not thread-safe**, so don't share a single *Storage* object between instances of *Bayes* in multiple threads.

Then you perform your training or checking for spam operations.

Finally, you should call *storage.finish()* to make sure your data are saved to file.


### Training

For a Bayesian antispam filtering system to work, you should train it on bad (spam) and good (ham, or not spam) data. After you created objects as described above, interact with an instance of *Bayes* object:

	spam_message = "Viagra, cialis for $2.59!!! Call 555-54-53"
	bayes.train(spam_message, True)
	
	ham_message = "Paul Graham doesn't need Viagra. He is NP-hard."
	bayes.train(ham_message, False)
	
#### Explanation

*train()* takes two arguments:

*message*

Text for training.

*is_spam*

Indicates if given message is spam.


### Checking for spam

After you trained your system with enough data, you can rate or check messages using one of the two methods: *is_spam()* or *spam_rating()*. Let's use both with data trained above.

	m1 = "Cheap viagra for 2.59"
	bayes.is_spam(m1)       # => True
	bayes.spam_rating(m1)   # => 0.97
	
	m2 = "I don't use viagra (yet)"
	bayes.is_spam(m2)       # => False
	bayes.spam_rating(m2)   # => 0.16  
	
#### Explanation

Both methods take text message you want to check for spam as an argument.

*spam_rating()* calculates and returns probability of a message to be spam (from 0 to 1).

*is_spam()* simply calls *spam_rating()* and checks if probability is more than 0.9.


Using PyBayesAntispam from shell
--------------------------------

You can use PyBayesAntispam as a stand-alone executable.

Since training data is loaded on every execution, it's currently inefficient to use PyBayesAntispam from shell with large training databases and a lot of messages.

#### Usage

	Usage: bayes.py [option] datafile < infile

	Options:
			-s, --train-spam - train datafile with infile as spam
			-h, --train-ham - train datafile with infile as ham
			-c, --check - check for spam rating of infile

#### Examples

To train *bayes.dat* with *spam.txt* as spam:

	bayes.py -s bayes.dat < spam.txt

To train *bayes.dat* with a given message as ham (not spam):

	echo -n "Not a spammy message" | bayes.py -h bayes.dat

To check *message.txt* against *bayes.dat* for spam:

	bayes -c bayes.dat < message.txt

This will output spam rating of *message.txt*.

Another example of checking:

	$ echo "I don't use viagra (yet)" | ./bayes.py -c test.dat
	0.16


Implementation details
----------------------

### Storage

Storage stores database of tokens using cPickle (since it seems like an efficient way to store binary data [ref. 1]). Data values stored in file are *totals* and *tokens*.

Totals is a simple dictionary:

	totals = {'spam':integer, 'ham':integer}


Tokens is a dictionary of lists with the following schema:

	tokens[hash] = [ham_count, spam_count]

As you can see, it doesn't store actual word, only its hash (calculated using Python's *hash()* function).

### Bayes

When you train your filter with a message, *totals['spam']* (or *totals['ham']* if the message is ham) in storage is incremented by 1, and *tokens* for each word (token) are incremented by 1 accordingly.

When you check a message, probabilities are being calculated [ref. 2] from *totals* and *tokens*:

		    			p1 * p2 * ... * pN
	p = -----------------------------------------------------
	      p1 * p2 * ... * pN + (1 - p1) * (1 - p2) * (1 - p3)
	
where:
 	
* *p* is the probability (rating) that the given message is spam.
* *pN* is the probability that it is a spam knowing it contains a Nth token.

pN is calculated using the following formula:        
    
					spam_count / totals_spam
	pN = ------------------------------------------------------
	        (ham_count / total_ham) + (spam_count / total_spam)

where *spam\_count* and *ham\_count* are counts for a given token.

#### Default probabilities [ref. 3]

Token has 0 hams, 1 or more spams: 0.99

Token has 0 spams, 1 or more hams: 0.01

Token is not in database: 0.04 

Message is spam (as used by *is_spam()* function): > 0.9

#### Token separation

* Everything between whitespace or separator characters are tokens (e.g. "Hello, there!!! Nice weather?" is split to ["hello", "there", "nice", "weather"])...

* ...except that dot between digits is not a separator (e.g. "Address 192.168.1.3" is ["address", "192.168.1.3"], or "$10.80 payment" is ["$10.80", "payment"]) [ref. 4]

* Tokens are case insensitive (e.g. "spam" and "SPAM" has the same probability), i.e. they are converted to lowercase. It should work better for small training databases.

* Dashes between words are preserved (e.g. "know-how" is a single token, but "hey - you" are two tokens, "hey" and "you").

* Tokens with 2 or less characters are not considered (e.g "this is not me" is two tokens "this" and "not".)

(Finally, as said before, tokens are not words, but hash(token).)

### References

1. Didip Kerabat. [Python: cPickle vs ConfigParser vs Shelve Performance](http://rapd.wordpress.com/2009/03/26/python-cpickle-vs-configparser-vs-shelve-performance/), 2009
2. -. [Bayesian Spam Filtering](http://en.wikipedia.org/wiki/Bayesian_spam_filtering). *Wikipedia*.
3. Paul Graham. [A Plan for Spam](http://www.paulgraham.com/spam.html), 2002
4. Paul Graham. [Better Bayesian Filtering](http://www.paulgraham.com/better.html), 2003