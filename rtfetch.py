#!/usr/bin/env python
#
#    rtfetch -- Update rtorrent files from popular trackers
#    Copyright (C) 2012  Devaev Maxim <mdevaev@gmail.com>
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
#####


import sys
import os
import socket
import operator
import shutil
import datetime

from ulib import fmt
from ulib import ui
import ulib.ui.cli # pylint: disable=W0611

from rtlib import tfile
from rtlib import fetcherlib
from rtlib import fetchers
from rtlib import clientlib
from rtlib import clients
from rtlib import config


##### Public constants #####
DELIMITER = "-" * 10


##### Public methods #####
def updateTorrent(torrent, fetcher, backup_dir_path, backup_suffix, client, save_customs_list, real_update_flag) :
	new_data = fetcher.fetchTorrent(torrent)
	tmp_torrent = tfile.Torrent()
	tmp_torrent.loadData(new_data)
	diff_tuple = tfile.diff(torrent, tmp_torrent)

	if real_update_flag :
		if not backup_dir_path is None :
			backup_suffix = datetime.datetime.now().strftime(backup_suffix)
			backup_file_path = os.path.join(backup_dir_path, os.path.basename(torrent.path()) + backup_suffix)
			shutil.copyfile(torrent.path(), backup_file_path)

		if not client is None :
			if len(save_customs_list) != 0 :
				customs_dict = client.customs(torrent, save_customs_list)
			prefix = client.dataPrefix(torrent)
			client.removeTorrent(torrent)

		with open(torrent.path(), "wb") as torrent_file :
			torrent_file.write(new_data)
		torrent.loadData(new_data, torrent.path())

		if not client is None :
			client.loadTorrent(torrent, prefix)
			if len(save_customs_list) != 0 :
				client.setCustoms(torrent, customs_dict)

	return diff_tuple

def torrents(src_dir_path, names_filter) :
	torrents_list = list(tfile.torrents(src_dir_path, abs_flag=True).items())
	if not names_filter is None :
		torrents_list = [ item for item in torrents_list if names_filter in item[0] ]
	return sorted(torrents_list, key=operator.itemgetter(0))

def readCaptchaCallback(url) :
	print("# Enter the captcha from [ %s ] ?>" % (url))
	return input()

def makeColored(no_colors_flag, force_colors_flag) :
	if not no_colors_flag :
		return ( lambda code, text : ui.term.colored(code, text, force_colors_flag) )
	else :
		return ( lambda code, text : text )


###
def update( # pylint: disable=R0913
		fetchers_list,
		client,
		src_dir_path,
		backup_dir_path,
		backup_suffix,
		names_filter,
		save_customs_list,
		skip_unknown_flag,
		pass_failed_login_flag,
		show_passed_flag,
		show_diff_flag,
		real_update_flag,
		no_colors_flag,
		force_colors_flag,
	) :

	colored = makeColored(no_colors_flag, force_colors_flag)

	invalid_count = 0
	not_in_client_count = 0
	unknown_count = 0
	passed_count = 0
	updated_count = 0
	error_count = 0

	torrents_list = torrents(src_dir_path, names_filter)
	hashes_list = ( client.hashes() if not client is None else [] )

	for (count, (torrent_file_name, torrent)) in enumerate(torrents_list) :
		status_line = "[$sign$] %s $fetcher$ %s" % (fmt.formatProgress(count + 1, len(torrents_list)), torrent_file_name)
		format_fail = ( lambda error, code = (31, 1), sign = "!" : ( status_line
				.replace("$sign$", colored(code, sign), 1)
				.replace("$fetcher$", colored(code, error), 1)
			))

		if torrent is None :
			ui.cli.newLine(format_fail("INVALID_TORRENT"))
			invalid_count += 1
			continue

		status_line += " --- %s" % (torrent.comment() or "")

		if not client is None and not torrent.hash() in hashes_list :
			ui.cli.newLine(format_fail("NOT_IN_CLIENT"))
			not_in_client_count += 1
			continue

		fetcher = fetcherlib.selectFetcher(torrent, fetchers_list)
		if fetcher is None :
			unknown_count += 1
			if not skip_unknown_flag :
				ui.cli.newLine(format_fail("UNKNOWN", (33, 1), " "))
			continue

		status_line = status_line.replace("$fetcher$", colored((36, 1), fetcher.plugin()), 1)
		format_sign = ( lambda color, sign : status_line.replace("$sign$", ( colored(color, sign) if not color is None else sign ), 1) )
		try :
			if not fetcher.loggedIn() :
				ui.cli.newLine(format_sign((33, 1), "?"))
				error_count += 1
				continue

			if not fetcher.torrentChanged(torrent) :
				ui.cli.oneLine(format_sign(None, " "), not show_passed_flag)
				passed_count += 1
				continue

			diff_tuple = updateTorrent(torrent, fetcher, backup_dir_path, backup_suffix, client, save_customs_list, real_update_flag)
			ui.cli.newLine(format_sign((32, 1), "+"))
			if show_diff_flag :
				tfile.printDiff(diff_tuple, "\t", use_colors_flag=(not no_colors_flag), force_colors_flag=force_colors_flag)
			updated_count += 1

		except fetcherlib.CommonFetcherError as err :
			ui.cli.newLine(format_sign((31, 1), "-") + (" :: %s(%s)" % (type(err).__name__, err)))
			error_count += 1

		except Exception as err :
			ui.cli.newLine(format_sign((31, 1), "-"))
			ui.cli.printTraceback("\t")
			error_count += 1

	if ( (client and not_in_client_count) or (not skip_unknown_flag and unknown_count) or (show_passed_flag and passed_count) or
		invalid_count or updated_count or error_count ) :
		ui.cli.newLine("")
	ui.cli.newLine(DELIMITER)

	print("Invalid:       %d" % (invalid_count))
	if not client is None :
		print("Not in client: %d" % (not_in_client_count))
	print("Unknown:       %d" % (unknown_count))
	print("Passed:        %d" % (passed_count))
	print("Updated:       %d" % (updated_count))
	print("Errors:        %d" % (error_count))


###
def initFetchers(
		config_dict,
		url_retries,
		url_sleep_time,
		timeout,
		user_agent,
		client_agent,
		proxy_url,
		interactive_flag,
		only_fetchers_list,
		exclude_fetchers_list,
		pass_failed_login_flag,
		no_colors_flag,
		force_colors_flag,
	) :

	colored = makeColored(no_colors_flag, force_colors_flag)

	fetchers_list = []
	for fetcher_name in set(fetchers.FETCHERS_MAP.keys()).intersection(only_fetchers_list).difference(exclude_fetchers_list) :
		get_fetcher_option = ( lambda option : config.getOption(fetcher_name, option, config_dict) )
		get_common_option = ( lambda option, cli_value : config.getCommonOption((
			config.SECTION_MAIN, config.SECTION_RTFETCH, fetcher_name), option, config_dict, cli_value) )

		fetcher_class = fetchers.FETCHERS_MAP[fetcher_name]
		if fetcher_name in config_dict :
			ui.cli.oneLine("# Enabling the fetcher \"%s\"..." % (colored((36, 1), fetcher_name)))

			fetcher = fetcher_class(
				get_fetcher_option(config.OPTION_LOGIN),
				get_fetcher_option(config.OPTION_PASSWD),
				get_common_option(config.OPTION_URL_RETRIES, url_retries),
				get_common_option(config.OPTION_URL_SLEEP_TIME, url_sleep_time),
				get_common_option(config.OPTION_TIMEOUT, timeout),
				get_common_option(config.OPTION_USER_AGENT, user_agent),
				get_common_option(config.OPTION_CLIENT_AGENT, client_agent),
				get_common_option(config.OPTION_PROXY_URL, proxy_url),
				get_common_option(config.OPTION_INTERACTIVE, interactive_flag),
				readCaptchaCallback,
			)

			try :
				fetcher.ping()
				fetcher.login()
				ui.cli.newLine("# Fetcher \"%s\" is %s (user: %s; proxy: %s; interactive: %s)" % (
						colored((36, 1), fetcher_name),
						colored((32, 1), "ready"),
						( fetcher.userName() or "<anonymous>" ),
						( fetcher.proxyUrl() or "<none>" ),
						( "yes" if fetcher.isInteractive() else "no" ),
					))
			except Exception as err :
				ui.cli.newLine("# Init error: %s: %s(%s)" % (
						colored((36, 1), fetcher_name),
						colored((31, 1), type(err).__name__),
						err,
					))
				if not pass_failed_login_flag :
					raise
			fetchers_list.append(fetcher)
	return fetchers_list


##### Main #####
def main() :
	(cli_parser, config_dict, argv_list) = config.partialParser(sys.argv[1:], description="Update rtorrent files from popular trackers")
	config.addArguments(cli_parser,
		config.ARG_SOURCE_DIR,
		config.ARG_BACKUP_DIR,
		config.ARG_BACKUP_SUFFIX,
		config.ARG_NAMES_FILTER,
		config.ARG_ONLY_FETCHERS,
		config.ARG_EXCLUDE_FETCHERS,
		config.ARG_TIMEOUT,
		config.ARG_INTERACTIVE,
		config.ARG_NO_INTERACTIVE,
		config.ARG_SKIP_UNKNOWN,
		config.ARG_NO_SKIP_UNKNOWN,
		config.ARG_PASS_FAILED_LOGIN,
		config.ARG_NO_PASS_FAILED_LOGIN,
		config.ARG_SHOW_PASSED,
		config.ARG_NO_SHOW_PASSED,
		config.ARG_SHOW_DIFF,
		config.ARG_NO_SHOW_DIFF,
		config.ARG_CHECK_VERSIONS,
		config.ARG_NO_CHECK_VERSIONS,
		config.ARG_REAL_UPDATE,
		config.ARG_NO_REAL_UPDATE,
		config.ARG_URL_RETRIES,
		config.ARG_URL_SLEEP_TIME,
		config.ARG_USER_AGENT,
		config.ARG_CLIENT_AGENT,
		config.ARG_PROXY_URL,
		config.ARG_CLIENT,
		config.ARG_CLIENT_URL,
		config.ARG_SAVE_CUSTOMS,
		config.ARG_NO_COLORS,
		config.ARG_USE_COLORS,
		config.ARG_FORCE_COLORS,
		config.ARG_NO_FORCE_COLORS,
	)
	raw_options = cli_parser.parse_args(argv_list)
	cli_options = config.syncParsers(config.SECTION_RTFETCH, raw_options, config_dict, (
			# For fetchers: validate this options later
			config.OPTION_LOGIN,
			config.OPTION_PASSWD,
			config.OPTION_URL_RETRIES,
			config.OPTION_URL_SLEEP_TIME,
			config.OPTION_USER_AGENT,
			config.OPTION_CLIENT_AGENT,
			config.OPTION_PROXY_URL,
			config.OPTION_INTERACTIVE,
		))

	colored = makeColored(cli_options.no_colors_flag, cli_options.force_colors_flag)
	socket.setdefaulttimeout(cli_options.timeout)

	fetchers_list = initFetchers(config_dict,
		raw_options.url_retries,
		raw_options.url_sleep_time,
		raw_options.timeout,
		raw_options.user_agent,
		raw_options.client_agent,
		raw_options.proxy_url,
		raw_options.interactive_flag,
		cli_options.only_fetchers_list,
		cli_options.exclude_fetchers_list,
		cli_options.pass_failed_login_flag,
		cli_options.no_colors_flag,
		cli_options.force_colors_flag,
	)
	if len(fetchers_list) == 0 :
		print("No available fetchers in config", file=sys.stderr)
		sys.exit(1)
	if (len(cli_options.only_fetchers_list) != 0 or len(cli_options.exclude_fetchers_list) != 0) and raw_options.skip_unknown_flag is None :
		cli_options.skip_unknown_flag = True

	if cli_options.check_versions_flag and not fetcherlib.checkVersions(fetchers_list) :
		sys.exit(1)

	client = None
	if not cli_options.client_name is None :
		client = clientlib.initClient(
			clients.CLIENTS_MAP[cli_options.client_name],
			cli_options.client_url,
			save_customs_list=cli_options.save_customs_list,
		)

	if not cli_options.real_update_flag :
		print("#", colored((31, 1), "WARNING! Running mode NOOP. For a real operation, use the option -e/--real-update"))

	print()
	update(fetchers_list, client,
		cli_options.src_dir_path,
		cli_options.backup_dir_path,
		cli_options.backup_suffix,
		cli_options.names_filter,
		cli_options.save_customs_list,
		cli_options.skip_unknown_flag,
		cli_options.pass_failed_login_flag,
		cli_options.show_passed_flag,
		cli_options.show_diff_flag,
		cli_options.real_update_flag,
		cli_options.no_colors_flag,
		cli_options.force_colors_flag,
	)
	print()


###
if __name__ == "__main__" :
	main()

