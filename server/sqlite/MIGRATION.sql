-- This migrates the old database to support pretendo. Don't forget to backup the database first.
ALTER TABLE friends
ADD network tinyint; 
UPDATE friends set network=0