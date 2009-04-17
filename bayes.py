#!/usr/bin/env python

# bayes.py - Bayesian spam rating
# MIT License
#
# Copyright (c) 2009 Dmitry Chestnykh, Coding Robots 
#                    http://www.codingrobots.com
#  
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#  
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#  
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.


import cPickle as pickle
import re, string
import fcntl
import sys, getopt
import operator

class Storage:
    def __init__(self, filename, min_save_count=5):
        self.filename = filename
        self.totals = None
        self.tokens = None
        self.save_count = 0
        self.min_save_count = min_save_count
        
    def load(self):
        """Load data from file"""
        f = open(self.filename, 'rb')
        self.totals, self.tokens = pickle.load(f)
        f.close()
    
    def save(self):
        """Save data to file"""
        if self.totals and self.tokens:
            f = open(self.filename, 'wb')
            fcntl.flock(f.fileno(), fcntl.LOCK_EX)
            pickle.dump([self.totals, self.tokens], f, -1)
            f.close()
    
    def save_if_needed(self):
        """ 
        Increase save_count and save data to file if
        it's >=max_save_count 
        """
        self.save_count += 1
        if self.save_count >= self.min_save_count:
            self.save()
            self.save_count = 0
            
    def finish(self):
        if self.save_count > 0:
            self.save()
            
class Bayes:

    TOKENS_RE = re.compile(r"[\s\:;\(\)\?\"\!\/]+|--|\D\./u")

    def __init__(self, storage):
        self.storage = storage            
    
    def __get_words_list(self, message):
        """Return list of tokens (words) from string message"""
        # split message to words 
        # (remove separators everywhere except for numbers with dots)
        words = self.TOKENS_RE.split(message)
        # filter out words that has 2 or less characters
        words = filter(lambda s: len(s) > 2, words)
        return words
        
    def train(self, message, is_spam):
        """Train database with message"""
        totals = self.storage.totals
        tokens = self.storage.tokens
        if not totals:
            totals = {'spam':0, 'ham':0}
            self.storage.totals = totals
        if is_spam:
            totals['spam'] += 1
        else:
            totals['ham'] += 1
        if not tokens:
            tokens = {}
            self.storage.tokens = tokens
        
        # compute hashes of uppercase words
        hashes = map(lambda x: hash(string.upper(x)), \
                     self.__get_words_list(message))
        for h in hashes:
            try:
                t = tokens[h]
                if is_spam:
                    t[1] += 1  # spam_count
                else:
                    t[0] += 1  # ham_count
            except KeyError:
                # no word in storage
                spam_count = 1 if is_spam else 0
                ham_count = 1 - spam_count
                tokens[h] = [ham_count, spam_count]
        self.storage.save_if_needed()
            
            
    def spam_rating(self, message):
        """Calculate and return spam rating of message"""
        totals = self.storage.totals
        if not totals:
            return 0.4
        total_spam = totals['spam']
        total_ham = totals['ham']
        tokens = self.storage.tokens
        if not tokens:
            return 0.4

        p = 1.0
        omp = 1.0
        
        hashes = map(lambda x: hash(string.upper(x)), \
                     self.__get_words_list(message))
        ratings = []
        for h in hashes:
            try:
                ham_count, spam_count = tokens[h]
                # ham_count *= 2  # this increases weight of ham
                if spam_count > 0 and ham_count == 0:
                    rating = 0.99
                elif spam_count == 0 and ham_count > 0:
                    rating = 0.01
                elif total_spam > 0 and total_ham > 0:
                    ham_prob = float(ham_count) / float(total_ham)
                    spam_prob = float(spam_count) / float(total_spam)
                    rating = spam_prob / (ham_prob + spam_prob)
                    if rating < 0.01:
                        rating = 0.01
                else:
                    rating = 0.4 # normally this won't happen
            except KeyError:
                rating = 0.4 # never seen this word
            ratings.append(rating)

        if (len(ratings) > 20):
            # leave only 20 most "interesting" ratings: 
            # 10  hightest and 10 lowest
            ratings.sort()
            ratings = ratings[:10] + ratings[-10:]
                    
        try:
            p = reduce(operator.mul, ratings)
            omp = reduce(operator.mul, map(lambda r: 1.0-r, ratings))
            return p / (p + omp)
            #
            ### Robinson's method: http://tinyurl.com/robinsons
            ### Which one is better?
            # 
            # nth = 1./len(ratings)
            # P = 1.0 - reduce(operator.mul, \
            #           map(lambda p: 1.0-p, ratings), 1.0) ** nth
            # Q = 1.0 - reduce(operator.mul, ratings) ** nth
            # S = (P - Q) / (P + Q)
            # return (1 + S) / 2
            
        except ZeroDivisionError:
            return 0.5 # got float underflow, not sure about rating
        
    def is_spam(self, message):
        """Checks if message is spam.
         Message is considered spam if it's rating is more than 0.9
         """
        return self.spam_rating(message) > 0.9


#### Command-line things ####

def usage():
    """Prints command-line usage help"""
    print("Usage: bayes.py [option] datafile < infile")
    print("Options:")
    print("  -s, --train-spam - train datafile with infile as spam")
    print("  -h, --train-ham - train datafile with infile as ham")
    print("  -c, --check - check for spam rating of infile")

def main():
    try:
        opts, args = getopt.getopt(sys.argv[1:], "shc", 
                            ["help", "train-spam", "train-ham", "check"])
        if len(opts) == 0 or len(args) == 0:
            raise getopt.error("no options or argumens")
    except getopt.error, msg:
        print(msg)
        usage()
        sys.exit(2)

    storage = Storage(args[0])
    try:
        storage.load()
    except IOError:
        print("Creating database")
    bayes = Bayes(storage)
    # process options
    for o, a in opts:
        if o in ("--help", ""):
            usage()
            sys.exit(0)
        elif o in ("-s", "--train-spam"):
            bayes.train(sys.stdin.read(), True)
            print("Trained as spam")
        elif o in ("-h", "--train-ham"):
            bayes.train(sys.stdin.read(), False)
            print("Trained as ham")
        elif o in ("-c", "--check"):
            print("%.2f" % bayes.spam_rating(sys.stdin.read()))
        else:
            assert False, "unhandled option"
    storage.finish()
        
if __name__ == "__main__":
    main()
