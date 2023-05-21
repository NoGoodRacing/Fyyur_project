# ----------------------------------------------------------------------------#
# Imports
# ----------------------------------------------------------------------------#

import os

import dateutil.parser
import babel
from flask import Flask, render_template, request, \
    flash, redirect, url_for, abort, jsonify
from flask_moment import Moment
import logging
from logging import Formatter, FileHandler
from sqlalchemy import func
from forms import *
from flask_migrate import Migrate
from models import db, Venue, Artist, Show

# ----------------------------------------------------------------------------#
# App Config.
# ----------------------------------------------------------------------------#

app = Flask(__name__)
moment = Moment(app)
app.config.from_object('config')
db.init_app(app)
migration = Migrate(app, db)

with app.app_context():
    db.create_all()


# ----------------------------------------------------------------------------#
# Filters.
# ----------------------------------------------------------------------------#

def format_datetime(value, format='medium'):
    date = dateutil.parser.parse(value)
    if format == 'full':
        format = "EEEE MMMM, d, y 'at' h:mma"
    elif format == 'medium':
        format = "EE MM, dd, y h:mma"
    return babel.dates.format_datetime(date, format, locale='en')


app.jinja_env.filters['datetime'] = format_datetime


# ----------------------------------------------------------------------------#
# Controllers.
# ----------------------------------------------------------------------------#

@app.route('/')
def index():
    return render_template('pages/home.html')


#  Venues
#  ----------------------------------------------------------------

@app.route('/venues')
def venues():
    try:
        query = db.session.query(func.json_build_object(
            'city', Venue.city,
            'state', Venue.state,
            'venues', func.array_agg(
                func.json_build_object(
                    'id', Venue.id,
                    'name', Venue.name,
                    'num_upcoming_shows', Venue.upcoming_shows_count
                )
            ))).group_by(Venue.city, Venue.state)
        data = [i[0] for i in query]
        return render_template('pages/venues.html', areas=data)
    except Exception as err:
        if getattr(err, 'code', None) == 500:
            server_error(abort(500))
        else:
            print(err)


@app.route('/venues/search', methods=['POST'])
def search_venues():
    try:
        query = Venue.query. \
            filter(Venue.name.ilike(f"%{request.form.get('search_term')}%"))
        data_list = [{
            'id': v.id,
            'name': v.name,
            'num_upcoming_shows': v.upcoming_shows_count
        } for v in query]
        response = {'count': len(data_list), 'data': data_list}
        return render_template('pages/search_venues.html', results=response,
                               search_term=request.form.get('search_term', ''))
    except Exception as err:
        if getattr(err, 'code', None) == 500:
            server_error(abort(500))
        else:
            print(err)


@app.route('/venues/<int:venue_id>')
def show_venue(venue_id):
    # shows the venue page with the given venue_id
    # try:
    #     data = Venue.query.get_or_404(venue_id)
    #     return render_template('pages/show_venue.html', venue=data)
    # except Exception as err:
    #     if err.code == 404:
    #         not_found_error(abort(404))
    #     else:
    #         server_error(abort(500))

    try:
        venue = Venue.query.get_or_404(venue_id)
        venue_dict = dict(
            (col, getattr(venue, col)) for col in venue.__table__.columns.keys()
        )

        upcoming_shows = db.session.query(
            func.array_agg(
                func.json_build_object(
                    'artist_id', Artist.id,
                    'artist_name', Artist.name,
                    'artist_image_link', Artist.image_link,
                    'start_time', Show.start_time
                )
            ),
            func.count(Show.venue_id)
        ) \
            .select_from(Artist) \
            .join(Show) \
            .filter(Show.venue_id == venue_id, Show.start_time > datetime.now()).first()

        past_shows = db.session.query(
            func.array_agg(
                func.json_build_object(
                    'artist_id', Artist.id,
                    'artist_name', Artist.name,
                    'artist_image_link', Artist.image_link,
                    'start_time', Show.start_time
                )
            ),
            func.count(Show.venue_id)
        ) \
            .select_from(Artist) \
            .join(Show) \
            .filter(Show.venue_id == venue_id, Show.start_time < datetime.now()).first()

        data = venue_dict | {'upcoming_shows': upcoming_shows[0],
                             'upcoming_shows_count': upcoming_shows[1],
                             'past_shows': past_shows[0],
                             'past_shows_count': past_shows[1]}
        if not data['upcoming_shows']:
            data['upcoming_shows'] = []
        if not data['past_shows']:
            data['past_shows'] = []
        return render_template('pages/show_venue.html', venue=data)
    except Exception as err:
        if getattr(err, 'code', None) == 500:
            server_error(abort(500))
        if getattr(err, 'code', None) == 404:
            server_error(abort(404))
        else:
            print(err)


#  Create Venue
#  ----------------------------------------------------------------

@app.route('/venues/create', methods=['GET'])
def create_venue_form():
    form = VenueForm()
    return render_template('forms/new_venue.html', form=form)


@app.route('/venues/create', methods=['POST'])
def create_venue_submission():
    form = VenueForm(request.form, meta={'csrf': False})
    if form.validate():
        try:
            venue = Venue(
                name=form.name.data,
                city=form.city.data,
                state=form.state.data,
                address=form.address.data,
                phone=form.phone.data,
                image_link=form.image_link.data,
                facebook_link=form.facebook_link.data,
                website=form.website_link.data,
                seeking_talent=form.seeking_talent.data,
                seeking_description=form.seeking_description.data,
                genres=form.genres.data
            )
            db.session.add(venue)
            db.session.commit()
            flash('Venue ' + form.name.data + ' was successfully listed!')
            return redirect(url_for('index'))
        except Exception as err:
            db.session.rollback()
            flash(f"An error occurred. Venue {form.name.data} couldn't be listed")
            if getattr(err, 'code', None) == 500:
                server_error(abort(500))
            else:
                print(err)
        finally:
            db.session.close()
    else:
        message = []
        for field, err in form.errors.items():
            message.append(field + ' ' + '|'.join(err))
        flash('Errors ' + str(message))
        form = VenueForm()
        return render_template('forms/new_venue.html', form=form)


@app.route('/venues/<venue_id>', methods=['DELETE'])
def delete_venue(venue_id):
    try:
        Venue.query.filter_by(id=venue_id).delete()
        db.session.commit()
        return jsonify({'success': True})
    except Exception as err:
        db.session.rollback()
        if getattr(err, 'code', None) == 500:
            server_error(abort(500))
        else:
            print(err)
    finally:
        db.session.close()


#  Artists
#  ----------------------------------------------------------------
@app.route('/artists')
def artists():
    try:
        artists_list = Artist.query.all()
        data = [{'id': a.id, 'name': a.name} for a in artists_list]
        return render_template('pages/artists.html', artists=data)
    except Exception as err:
        if getattr(err, 'code', None) == 500:
            server_error(abort(500))
        else:
            print(err)


@app.route('/artists/search', methods=['POST'])
def search_artists():
    try:
        query = Artist.query. \
            filter(Artist.name.ilike(f'%{request.form.get("search_term")}%')).all()
        data_list = [{'id': a.id,
                      'name': a.name,
                      'num_upcoming_shows': a.upcoming_shows_count} for a in query]
        response = {'count': len(query), 'data': data_list}
        return render_template('pages/search_artists.html', results=response,
                               search_term=request.form.get('search_term', ''))
    except Exception as err:
        if getattr(err, 'code', None) == 500:
            server_error(abort(500))
        else:
            print(err)


@app.route('/artists/<int:artist_id>')
def show_artist(artist_id):
    # shows the artist page with the given artist_id
    # try:
    #     data = Artist.query.get_or_404(artist_id)
    #     return render_template('pages/show_artist.html', artist=data)
    # except Exception as err:
    #     if getattr(err, 'code', None) == 500:
    #         server_error(abort(500))
    #     if getattr(err, 'code', None) == 404:
    #         server_error(abort(404))
    #     else:
    #         print(err)

    try:
        artist = Artist.query.get_or_404(artist_id)
        artist_dict = dict(
            (col, getattr(artist, col)) for col in artist.__table__.columns.keys()
        )

        upcoming_shows = db.session.query(
            func.array_agg(
                func.json_build_object(
                    'venue_id', Venue.id,
                    'venue_name', Venue.name,
                    'venue_image_link', Venue.image_link,
                    'start_time', Show.start_time
                )
            ),
            func.count(Show.venue_id)
        ) \
            .select_from(Venue) \
            .join(Show) \
            .filter(Show.artist_id == artist_id, Show.start_time > datetime.now()).first()

        past_shows = db.session.query(
            func.array_agg(
                func.json_build_object(
                    'venue_id', Venue.id,
                    'venue_name', Venue.name,
                    'venue_image_link', Venue.image_link,
                    'start_time', Show.start_time
                )
            ),
            func.count(Show.venue_id)
        ) \
            .select_from(Venue) \
            .join(Show) \
            .filter(Show.artist_id == artist_id, Show.start_time < datetime.now()).first()

        data = artist_dict | {'upcoming_shows': upcoming_shows[0],
                              'upcoming_shows_count': upcoming_shows[1],
                              'past_shows': past_shows[0],
                              'past_shows_count': past_shows[1]}
        if not data['upcoming_shows']:
            data['upcoming_shows'] = []
        if not data['past_shows']:
            data['past_shows'] = []
        return render_template('pages/show_artist.html', artist=data)
    except Exception as err:
        if getattr(err, 'code', None) == 500:
            server_error(abort(500))
        if getattr(err, 'code', None) == 404:
            server_error(abort(404))
        else:
            print(err)


#  Update
#  ----------------------------------------------------------------
@app.route('/artists/<int:artist_id>/edit', methods=['GET'])
def edit_artist(artist_id):
    form = ArtistForm()
    try:
        artist = Artist.query.get_or_404(artist_id)
        return render_template('forms/edit_artist.html',
                               form=form,
                               artist=artist)
    except Exception as err:
        if getattr(err, 'code', None) == 500:
            server_error(abort(500))
        if getattr(err, 'code', None) == 404:
            server_error(abort(404))
        else:
            print(err)


@app.route('/artists/<int:artist_id>/edit', methods=['POST'])
def edit_artist_submission(artist_id):
    artist = Artist.query.get_or_404(artist_id)
    form = ArtistForm(request.form, meta={'csrf': False}, obj=artist)
    if form.validate():
        try:
            form.populate_obj(artist)
            db.session.commit()
            return redirect(url_for('show_artist', artist_id=artist_id))
        except Exception as err:
            db.session.rollback()
            if getattr(err, 'code', None) == 500:
                server_error(abort(500))
            else:
                print(err)
        finally:
            db.session.close()
    else:
        message = []
        for field, err in form.errors.items():
            message.append(field + ' ' + '|'.join(err))
        flash('Errors ' + str(message))
        form = ArtistForm()
        return render_template('forms/edit_artist.html',
                               form=form,
                               artist=artist)


@app.route('/venues/<int:venue_id>/edit', methods=['GET'])
def edit_venue(venue_id):
    form = VenueForm()
    try:
        venue = Venue.query.get_or_404(venue_id)
        return render_template('forms/edit_venue.html', form=form, venue=venue)
    except Exception as err:
        if getattr(err, 'code', None) == 500:
            server_error(abort(500))
        if getattr(err, 'code', None) == 404:
            server_error(abort(404))
        else:
            print(err)
    finally:
        db.session.close()


@app.route('/venues/<int:venue_id>/edit', methods=['POST'])
def edit_venue_submission(venue_id):
    venue = Venue.query.get_or_404(venue_id)
    form = VenueForm(request.form, meta={'csrf': False}, obj=venue)
    if form.validate():
        try:
            form.populate_obj(venue)
            db.session.commit()
            return redirect(url_for('show_venue', venue_id=venue_id))
        except Exception as err:
            db.session.rollback()
            if getattr(err, 'code', None) == 500:
                server_error(abort(500))
            else:
                print(err)
        finally:
            db.session.close()
    else:
        message = []
        for field, err in form.errors.items():
            message.append(field + ' ' + '|'.join(err))
        flash('Errors ' + str(message))
        form = VenueForm()
        return render_template('forms/edit_venue.html', form=form, venue=venue)


#  Create Artist
#  ----------------------------------------------------------------

@app.route('/artists/create', methods=['GET'])
def create_artist_form():
    form = ArtistForm()
    return render_template('forms/new_artist.html', form=form)


@app.route('/artists/create', methods=['POST'])
def create_artist_submission():
    # called upon submitting the new artist listing form
    form = ArtistForm(request.form, meta={'csrf': False})
    if form.validate():
        try:
            artist = Artist(
                name=form.name.data,
                genres=form.genres.data,
                city=form.city.data,
                state=form.state.data,
                phone=form.phone.data,
                website=form.website_link.data,
                facebook_link=form.facebook_link.data,
                seeking_venue=form.seeking_venue.data,
                seeking_description=form.seeking_description.data,
                image_link=form.image_link.data,
            )
            db.session.add(artist)
            db.session.commit()
            flash('Artist ' + form.name.data + ' was successfully listed!')
            return redirect(url_for('index'))
        except Exception as err:
            db.session.rollback()
            flash(f'An error occurred. Artist {form.name.data} could not be listed.')
            if getattr(err, 'code', None) == 500:
                server_error(abort(500))
            else:
                print(err)
        finally:
            db.session.close()
    else:
        message = []
        for field, err in form.errors.items():
            message.append(field + ' ' + '|'.join(err))
        flash('Errors ' + str(message))
        form = ArtistForm()
        return render_template('forms/new_artist.html', form=form)


#  Shows
#  ----------------------------------------------------------------

@app.route('/shows')
def shows():
    # displays list of shows at /shows
    try:
        shows_list = Show.query.all()
        data = [{
            'venue_id': i.venue_id,
            'venue_name': i.venues.name,
            'artist_id': i.artist_id,
            'artist_name': i.artists.name,
            'artist_image_link': i.artists.image_link,
            'start_time': str(i.start_time)
        } for i in shows_list]
        return render_template('pages/shows.html', shows=data)
    except Exception as err:
        if getattr(err, 'code', None) == 500:
            server_error(abort(500))
        else:
            print(err)


@app.route('/shows/create')
def create_shows():
    # renders form. do not touch.
    form = ShowForm()
    return render_template('forms/new_show.html', form=form)


@app.route('/shows/create', methods=['POST'])
def create_show_submission():
    form = ShowForm(request.form, meta={'csrf': False})
    if form.validate():
        try:
            show = Show(
                artist_id=form.artist_id.data,
                venue_id=form.venue_id.data,
                start_time=form.start_time.data
            )
            db.session.add(show)
            db.session.commit()
            flash('Show was successfully listed!')
            return redirect(url_for('index'))
        except Exception as err:
            db.session.rollback()
            flash('An error occurred. Show could not be listed.')
            if getattr(err, 'code', None) == 500:
                server_error(abort(500))
            else:
                print(err)
            return render_template('forms/new_show.html', form=form)
        finally:
            db.session.close()
    else:
        message = []
        for field, err in form.errors.items():
            message.append(field + ' ' + '|'.join(err))
        flash('Errors ' + str(message))
        form = ShowForm()
        return render_template('forms/new_show.html', form=form)


@app.errorhandler(404)
def not_found_error(error):
    return render_template('errors/404.html'), 404


@app.errorhandler(500)
def server_error(error):
    return render_template('errors/500.html'), 500


if not app.debug:
    file_handler = FileHandler('error.log')
    file_handler.setFormatter(
        Formatter('%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]')
    )
    app.logger.setLevel(logging.INFO)
    file_handler.setLevel(logging.INFO)
    app.logger.addHandler(file_handler)
    app.logger.info('errors')

# ----------------------------------------------------------------------------#
# Launch.
# ----------------------------------------------------------------------------#

# Default port:
# if __name__ == '__main__':
#     app.run()

# Or specify port manually:

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
