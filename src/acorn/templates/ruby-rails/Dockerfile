FROM ruby:{{ruby_version}}-slim

RUN apt-get update -qq && apt-get install -y build-essential libpq-dev

WORKDIR /app
COPY Gemfile Gemfile.lock ./
RUN bundle install
COPY . .

EXPOSE {{port}}
CMD ["rails", "server", "-b", "0.0.0.0"]
