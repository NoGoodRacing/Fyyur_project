from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import func, and_, select
from sqlalchemy.ext.hybrid import hybrid_property

db = SQLAlchemy()


class Venue(db.Model):
    __tablename__ = 'venues'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String, nullable=False)
    city = db.Column(db.String(120), nullable=False)
    state = db.Column(db.String(120), nullable=False)
    address = db.Column(db.String(120), nullable=False)
    phone = db.Column(db.String(120))
    image_link = db.Column(db.String(500))
    facebook_link = db.Column(db.String(120), nullable=False)
    website = db.Column(db.String(120))
    seeking_talent = db.Column(db.Boolean)
    seeking_description = db.Column(db.Text)
    genres = db.Column(db.ARRAY(db.String), nullable=False)
    shows = db.relationship('Show', backref='venues', lazy=True)

    @hybrid_property
    def upcoming_shows(self):
        if self.shows:
            query = Show.query.filter(and_(Show.start_time > func.now(),
                                           Show.venue_id == self.id)).all()
            return [{"artist_id": i.artist_id,
                     "artist_name": i.artists.name,
                     "artist_image_link": i.artists.image_link,
                     "start_time": str(i.start_time)} for i in query]
        return []

    @hybrid_property
    def upcoming_shows_count(self):
        if self.upcoming_shows:
            return len(list(self.upcoming_shows))
        return 0

    @upcoming_shows_count.expression
    def upcoming_shows_count(cls):
        return select(func.count(Show.id)). \
            where(and_(Show.start_time > func.now(), Show.venue_id == cls.id))

    @hybrid_property
    def past_shows(self):
        if self.shows:
            query = Show.query.filter(and_(Show.start_time < func.now(),
                                           Show.venue_id == self.id)).all()
            return [{"artist_id": i.artist_id,
                     "artist_name": i.artists.name,
                     "artist_image_link": i.artists.image_link,
                     "start_time": str(i.start_time)} for i in query]
        return []

    @hybrid_property
    def past_shows_count(self):
        if self.past_shows:
            return len(list(self.past_shows))
        return 0


    def __repr__(self):
        return f'Venue: {self.name}'


class Artist(db.Model):
    __tablename__ = 'artists'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String, nullable=False)
    city = db.Column(db.String(120), nullable=False)
    state = db.Column(db.String(120), nullable=False)
    phone = db.Column(db.String(120), nullable=False)
    genres = db.Column(db.ARRAY(db.String), nullable=False)
    image_link = db.Column(db.String(500))
    facebook_link = db.Column(db.String(120), nullable=False)
    website = db.Column(db.String(120))
    seeking_venue = db.Column(db.Boolean)
    seeking_description = db.Column(db.Text)
    shows = db.relationship('Show', backref='artists', lazy=True,
                            cascade="all, delete")

    @hybrid_property
    def upcoming_shows(self):
        if self.shows:
            query = Show.query.filter(and_(Show.start_time > func.now(),
                                           Show.artist_id == self.id)).all()
            return [{"venue_id": i.venue_id,
                     "venue_name": i.venues.name,
                     "venue_image_link": i.venues.image_link,
                     "start_time": str(i.start_time)} for i in query]
        return []

    @hybrid_property
    def upcoming_shows_count(self):
        if self.upcoming_shows:
            return len(list(self.upcoming_shows))
        return 0

    @hybrid_property
    def past_shows(self):
        if self.shows:
            query = Show.query.filter(and_(Show.start_time < func.now(),
                                           Show.artist_id == self.id)).all()
            return [{"venue_id": i.venue_id,
                     "venue_name": i.venues.name,
                     "venue_image_link": i.venues.image_link,
                     "start_time": str(i.start_time)} for i in query]
        return []

    @hybrid_property
    def past_shows_count(self):
        if self.past_shows:
            return len(list(self.past_shows))
        return 0

    def __repr__(self):
        return f'Artist: {self.name}'


class Show(db.Model):
    __tablename__ = 'shows'

    id = db.Column(db.Integer, primary_key=True)
    artist_id = db.Column(db.Integer, db.ForeignKey('artists.id'))
    venue_id = db.Column(db.Integer, db.ForeignKey('venues.id',
                                                   ondelete="CASCADE"))
    start_time = db.Column(db.DateTime, nullable=False)
