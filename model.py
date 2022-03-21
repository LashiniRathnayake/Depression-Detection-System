import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import sklearn.metrics as sm
import re
import emoji
import nltk
nltk.download('punkt')
from nltk.tokenize import word_tokenize
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.neighbors import KNeighborsClassifier

data_set = pd.read_csv(r"Type Your Directory Path\dataset.csv")
print(data_set.head(10))

# Text cleaning of the dataset
def clean_text(df, text_field, new_text_field):
    df[new_text_field] = df[text_field]
    # remove numbers
    df[new_text_field] = df[new_text_field].apply(lambda elem: re.sub(r"\d+", "", elem))
    # remove url
    df[new_text_field] = df[new_text_field].apply(lambda elem: re.sub(r"https?://\S+|www\.\S+", "", elem))
    # remove HTML tags
    df[new_text_field] = df[new_text_field].apply(lambda elem: re.sub(r"<.*?>", "", elem))
    # remove emojis
    df[new_text_field] = df[new_text_field].apply(lambda elem: emoji.get_emoji_regexp().sub(r" ", elem))
    # remove re-tweets status
    df[new_text_field] = df[new_text_field].apply(lambda elem: re.sub(r'^RT @\w*: ', ' ', elem))
    # remove mentions
    df[new_text_field] = df[new_text_field].apply(lambda elem: re.sub(r'@\w*', ' ', elem))
    # remove special characters
    df[new_text_field] = df[new_text_field].apply(lambda elem: re.sub(r'[!@#&*$.?,]', ' ', elem))
    # remove \n
    df[new_text_field] = df[new_text_field].apply(lambda elem: re.sub(r'\n', ' ', elem))
    # remove ''
    df[new_text_field] = df[new_text_field].apply(lambda elem: re.sub("'", '', elem))
    # remove english letters
    df[new_text_field] = df[new_text_field].apply(lambda elem: re.sub(r'[a-z]', '', elem))
    df[new_text_field] = df[new_text_field].apply(lambda elem: re.sub(r'[A-Z]', '', elem))

    return df


# tokenizing
def tokenize(df, text_field, new_text_field):
    df[new_text_field] = df[text_field]
    df[new_text_field] = df[new_text_field].apply(word_tokenize)
    return df


clean_data = clean_text(data_set, 'Comment', 'text_clean')
tokenize_data = tokenize(data_set, 'text_clean', 'tokenized_text')
print(clean_data.head())

# Splitting the dataset into train and test subsets
# get the labels from the train data and assign to y
y = data_set.label.values

# use 70% to train and 30% to test
x_train, x_test, y_train, y_test = train_test_split(data_set.text_clean.values, y,
                                                    stratify=y,
                                                    random_state=1,
                                                    test_size=0.3, shuffle=True)

# Tf-idf Vectorizer to Vectorize the tweets
vectorizer = TfidfVectorizer(ngram_range=(1, 2),analyzer='word')
vectorizer.fit(list(x_train) + list(x_test))

# transform documents to document-term matrix transform comments into a vector/numerical form
x_train_vec = vectorizer.transform(x_train)
x_test_vec = vectorizer.transform(x_test)

# KNN as the classifier
k = 28
KNN = KNeighborsClassifier(n_neighbors = k).fit(x_train_vec,y_train)
prediction = KNN.predict(x_test_vec)

def classify_tweet(arr):
    return KNN.predict(vectorizer.transform(arr))

msg=["මට මානසික ගැටලුවක් තියෙනවා"]
print(classify_tweet(msg))
for index_instance,instance in enumerate(classify_tweet(msg)):
    print(msg[index_instance], ' - ',instance)

# define the stages of the pipeline
pipeline = Pipeline(steps= [('Tf-idfVectorizer', TfidfVectorizer(ngram_range=(1, 2),analyzer='word')),
                            ('model', KNeighborsClassifier(n_neighbors = 28))])

# fit the pipeline model with the training data
pipeline.fit(x_train, y_train)
# import joblib
from joblib import dump

# dump the pipeline model
dump(pipeline, filename="dep_classification.joblib")



