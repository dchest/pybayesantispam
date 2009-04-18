#!/usr/bin/env python
# -*- coding: utf8 -*-
"""
Unit tests for PyBayesAntispam
"""

import unittest
import os

import bayes

class TestSequenceFunctions(unittest.TestCase):
    
    TEMP_STORAGE = "/tmp/pybayes.test"
    MIN_SAVE_COUNT = 30
    
    def setUp(self):
        self.storage = bayes.Storage(self.TEMP_STORAGE, self.MIN_SAVE_COUNT)
        self.bayes = bayes.Bayes(self.storage)
        
    def tearDown(self):
        try:
            os.unlink(self.TEMP_STORAGE)
        except:
            pass
        
    def test_Storage_save_load(self):
        """Test loading and saving of storage data"""
        test_totals = {'spam':8999, 'ham':67}
        test_tokens = {}
        test_tokens[hash("one")] = [10, 5]
        test_tokens[hash("two")] = [0, 1]
        self.storage.totals = test_totals
        self.storage.tokens = test_tokens
        self.storage.save()
        self.storage.totals = None
        self.storage.tokens = None
        self.storage.load()
        self.assertEqual(self.storage.totals, test_totals, \
                "Storage loaded wrong totals or failed to load them")
        self.assertEqual(self.storage.tokens, test_tokens, \
                "Storage loaded wrong tokens or failed to load them")

    def test_Storage_saving_if_needed(self):
        """Test if storage saves properly with save_if_needed()"""
        for i in xrange(self.MIN_SAVE_COUNT-1):
            self.storage.save_if_needed()
            self.assertNotEqual(self.storage.save_count, 0, \
                        "Storage saved prematurely")
        self.storage.save_if_needed()
        self.assertEqual(self.storage.save_count, 0, \
                        "Storage didn't save or didn't updated save_count")
    
    def test_Storage_finish(self):
        """Test storage finish"""
        self.storage.save_if_needed()
        self.storage.finish()
        self.assertEqual(self.storage.save_count, 0, \
                        "Storage didn't save on finish")
        
    
    def test_Bayes__get_words_list(self):
        """Test tokenizer"""
        text = u"This!!! is tokenizer. Test, string?\nюникод two.words -- " + \
               "one-word 127.0.0.1 and $10.22 xxx!xxx... hey - you!!! Final."
        tokens = [u'This', u'tokenizer', u'Test', u'string', u'юникод',
                  u'two', u'words', u"one-word",
                  u'127.0.0.1', u'and', u'$10.22', u'xxx', u'xxx', 
                  u"hey", u"you", u"Final"]
        result = self.bayes._Bayes__get_words_list(text)
        self.assertEqual(result, tokens,
                     "Wrong tokenized results: " + repr(result))
        
    
    def add_train_data(self):
        spam = "This is spam."
        ham =  "This is ham."
        self.test_tokens = {
            hash('THIS'): [1,1], 
            hash('SPAM'): [0,1],
            hash('HAM') : [1,0],
        }
        self.bayes.train(spam, True)
        self.bayes.train(ham, False)
        
    def test_Bayes_train(self):
        self.add_train_data() 
        self.assertEqual(self.storage.totals, {'spam':1, 'ham':1},
                        "Wrong totals")
        self.assertEqual(self.storage.tokens, self.test_tokens,
            "Wrong tokens:\n%s\nmust be:\n%s" % \
                        (
                            repr(self.storage.tokens), 
                            repr(self.test_tokens)
                        ))
                        
    def test_Bayes_spam_rating(self):
        self.add_train_data()
        messages = [
                    # message, start_range, end_range
                    ("spam", 0.98, 1.00),
                    ("maybe, this is not!", 0.3, 0.4),
                    ("ham", 0.00, 0.01),
                    ("something cool", 0.00, 0.5),
                   ]
        for msg, r1, r2 in messages:
            rating = self.bayes.spam_rating(msg)
            self.assertTrue(r2 >= rating >= r1,
                "Wrong rating for '%s': %f, must be %f-%f" % \
                (msg, rating, r1, r2))
                
    def test_Bayes_is_spam(self):
        self.add_train_data()
        self.assertTrue(self.bayes.is_spam("spam"), 
                        "Spam marked as not spam")
        self.assertFalse(self.bayes.is_spam("something cool"), 
                        "Words not in database marked as spam")
        self.assertFalse(self.bayes.is_spam("ham"), 
                        "Ham marked as spam")
             
                
if __name__ == '__main__':
    unittest.main()
