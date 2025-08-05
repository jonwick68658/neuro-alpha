CREATE INDEX topic_name IF NOT EXISTS FOR (t:Topic) ON (t.name);
CREATE INDEX subtopic_name IF NOT EXISTS FOR (s:SubTopic) ON (s.name);
CREATE INDEX file_name IF NOT EXISTS FOR (f:File) ON (f.name)