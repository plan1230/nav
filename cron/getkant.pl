#!/usr/bin/perl

use File::Copy;
use SNMP_util;
use Net::hostent;
use Socket;
#use Mail::Sendmail;
use Pg;

my $eier = 'grohi@itea.ntnu.no';

my @felt = ("boksid","software","sysLoc","sysCon","ais");
#################################

# Setter error out til '/dev/null'
#open(STDERR, ">/dev/null");

my $ip2NetMask = ".1.3.6.1.2.1.4.20.1.3"; 


my $database = "manage";
my $conn = db_connect($database);
my $sql;
my $resultat;
my @line;

#########################################

# Setter error out til '/dev/null'
#open(STDERR, ">/dev/null");

# Dette forhindrer at det som vanligvis skrives til terminal, blir sendt i 
# mail. Gjelder f.eks passord osv.

##########################################

my %db = ();

&hent_db;

my %prefiksid = ();

&hent_prefiksid;

#my $linje = 0;

#%logg=();

# kan gj�re "sort by_ip"

foreach my $id (keys %boks)
{
#    print "$ip\n";

#    if ($boks{$id}{watch} eq 'f') 
	# Er pingbar, s� hvis den ikke svarer er det noe galt med community
#    {
	unless (&hent_data($id,$boks{$id}{ip},$boks{$id}{ro})){	
	    print "$boks{$id}{ro}\@$boks{$id}{ip} er ikke p� watch, men svarer ikke p� snmp.\n";
	}
 #   }    
 #   else
 #   {
#	print "$id2ip{$id} er p� watch, hopper over denne.\n";
#    }
}

foreach my $f (keys %boksinfo) {
    &sjekk(\%boksinfo, \%db_boksinfo, \@felt, "boksinfo", $f);
}   

#$tid = localtime(time);

#$LOGG = '>>/local/nettinfo/log/NTNUlog';
#open(LOGG,$LOGG);
#foreach $line (keys %logg)
#{
#   print LOGG "$logg{$line}\n";
#}

exit(0);

###########################################
sub sjekk {
    my %ny = %{$_[0]};
    my %gammel = %{$_[1]};
    my @felt = @{$_[2]};
    my $tabell = $_[3];
    my $f = $_[4];


#eksisterer i databasen?
    if($gammel{$f}[0]) {
#-----------------------
#UPDATE
	for my $i (0..$#felt ) {
	    unless($ny{$f}[$i] eq $gammel{$f}[$i]) {
#oppdatereringer til null m� ha egen sp�rring
		if ($ny{$f}[$i] eq "" && $gammel{$f}[$i] ne ""){
		    print "\nOppdaterer $f felt $felt[$i] fra \"$gammel{$f}[$i]\" til \"NULL\"";
		    $sql = "UPDATE $tabell SET $felt[$i]=null WHERE $felt[0]=\'$f\'";
		    db_execute($sql,$conn);
		    print $sql;
		} else {
#normal oppdatering
		    print "\nOppdaterer $f felt $felt[$i] fra \"$gammel{$f}[$i]\" til \"$ny{$f}[$i]\"";
		    $sql = "UPDATE $tabell SET $felt[$i]=\'$ny{$f}[$i]\' WHERE $felt[0]=\'$f\'";
		    print $sql;
		    db_execute($sql,$conn);
		}
	    }
	}
    }else{
#-----------------------
#INSERT
	print "\nSetter inn $ny{$f}[0]";
	my @val;
	my @key;
	foreach my $i (0..$#felt) {
	    if (defined($ny{$f}[$i]) && $ny{$f}[$i] ne ""){
		push(@val, "\'".$ny{$f}[$i]."\'");
		push(@key, $felt[$i]);
	    }
	}
	
	$sql = "INSERT INTO $tabell (".join(",",@key ).") VALUES (".join(",",@val).")";
	print $sql;
	db_execute($sql,$conn);
    }
}

#################################
sub hent_data
{
    my $id = $_[0];
    my $ip = $_[1];#$id2ip{$id};
    my $ro = $_[2];

    @res = &snmpwalk("$ro\@$ip","system");
    
    return 0 if (!$res[0]);

    (undef,my $SN) = split(/:/,$res[4]);
    (undef,my $SC) = split(/:/,$res[3]);
    (undef,my $SL) = split(/:/,$res[5]);
    chomp($SN);  chomp($SL); chomp($SC);
    
#    $nettel{$id}{sysName}     = $SN;
#    $boksinfo{$id}{sysLocation} = $SL;
#    $boksinfo{$id}{sysContact}  = $SC;

#sysName
    (my $sn) = &snmpget("$ro\@$ip","sysName");

# Sysname avsluttes ved 1. punktum.
    my $dummy;
    ($sn,$dummy) = split(/\./,$sn);
   
    return 0 if (!$sn);
   
    unless ($boks{$id}{sysName} eq $sn){
	$boks{$id}{sysName}= $sn;
#	&oppdater_en("boks","sysName",$sn,$felt[0],$id);
    }

#prefiksid
    my $prefiksid;
    @lines = &snmpget("$ro\@$ip","$ip2NetMask.$ip");
    my $nettadr;
    my $maske;
    foreach $line (@lines)
    {
        ($gwip,$netmask) = split(/:/,$line);
	$nettadr = &and_ip($gwip,$netmask);
	$maske = &mask_bits($netmask);
    }
    print $prefiksid = $prefiksid{$nettadr}{$maske};
    unless ($prefiksid){
	@lines = &snmpwalk("$ro\@$ip",$ip2NetMask);
	foreach $line (@lines)
	{
	    ($gwip,$netmask) = split(/:/,$line);
	    $nettadr = &and_ip($gwip,$netmask);
	    $maske = &mask_bits($netmask);
	    unless ($prefiksid = $prefiksid{$nettadr}{$maske}) {
		$prefiksid = &finn_prefiks($ip);
	    }
	    print "prefiksid = $prefiksid\n";
	}
    }
    print "ytre prefiksid  +++++++++ = $prefiksid\n";
    unless ($boks{$id}{prefiksid} =~ /$prefiksid/){
	$boks{$id}{prefiksid}= $prefiksid;
	&oppdater_en("boks","prefiksid",$prefiksid,$felt[0],$id);
    }

    #ais og software
    my ($SV,$ais) = &finn_sv($id,$ip);

    $boksinfo{$id} = [ $id,
		       $SV,
		       $SL,
		       $SC,
		       $ais ]; #ais
			   
   # print $boksinfo{$id}[0];
    return 1;
    
}



###########################################
sub hent_db
{
    $sql = "SELECT boksid,ip,sysName,prefiksid,watch,ro FROM boks WHERE kat=\'KANT\'";
    $resultat = db_select($sql,$conn);
    while (@line = $resultat->fetchrow)
    {
	@line = map rydd($_), @line;
	
	$boks{$line[0]}{ip}      = $line[1];
	$boks{$line[0]}{sysName} = $line[2];
	$boks{$line[0]}{prefiksid} = $line[3];
        $boks{$line[0]}{watch}   = $line[4];
        $boks{$line[0]}{ro}      = $line[5];
    }	    

    my $sql = "SELECT ".join(",",@felt)." FROM boksinfo";
    $resultat = db_select($sql,$conn);

    while (@line=$resultat->fetchrow)
    {
	@line = map rydd($_), @line;

	$db_boksinfo{$line[0]} = [ @line ];

    }
}

####################

sub ip2dns
{
    if ($h1 = gethost($_[0]))
    {
	$dnsname = $h1->name;
    }
    else
    {
	$dnsname = '-';
    }
    return $dnsname;
} # end sub ip2dns

#############################################
	
sub dns2ip
{
    if ($h2 = gethost($nettel{$_[0]}{sysName}.'.ntnu.no'))
    {
	$dnsip = inet_ntoa($h2->addr);
    }
    else
    {
	$dnsip = '-';
    }
    return $dnsip;

}   # end sub dns2ip

#############################################

sub finn_sv    # $sv  = software-versjon 
{
    my $id = $_[0];
    my $ip = $_[1]; #$id2ip{$id};
    my @temp = ("tull","");
    my $svmib = "";

#    if ($db_boksinfo{$id}{type} eq 'C1900')
#    {
#	$ret = '-';
#    }
#    else
#    {
	if ($db_boksinfo{$id}[5] =~ /PS40|SW1100|SW3300/) {
	    $svmib = '.1.3.6.1.4.1.43.10.27.1.1.1.12';
	    @temp = &snmpwalk("$db_boksinfo{$id}{ro}\@$ip","$svmib");
	} elsif ($db_boksinfo{$id}[5] =~ /PS10|Off8/) {  
	    $svmib = '.1.3.6.1.4.1.43.10.3.1.1.4.1';
	    @temp = &snmpwalk("$db_boksinfo{$id}{ro}\@$ip","$svmib");
	}
    (undef,my $ret) = split(/\:/,$temp[0]);
    (my $ais,undef) = split(/\:/,@temp[$#temp]);
    return ($ret,$ais);
#    }
}   # end sub finn_ais_og_sv


########################################################

sub by_ip
# sorterer paa ip "i samarbeid med" sort-funksjonen
# typisk kall: sort by_ip <...>
{
    ($aa,$ab,$ac,$ad)=split(/\./,$a);
    ($ba,$bb,$bc,$bd)=split(/\./,$b);    

    if ($ac < $bc){
	return -1;}
    elsif ($ac == $bc)
    {
	if ($ad < $bd)
	{return -1;}
	elsif ($ad == $bd)
	{return 0;}
	elsif ($ad > $bd)
	{return 1;}
    }
    if ($ac > $bc) {
	return 1;}
    
} # end sub by_ip

############################
sub and_ip {
    my @a =split(/\./,$_[0]);
    my @b =split(/\./,$_[1]);

    for (0..$#a) {
	$a[$_] = int($a[$_]) & int($b[$_]);
    }
    
    return join(".",@a);
}
##################################
sub mask_bits {
    $_ = $_[0];
    if    (/255.255.254.0/)   { return 23; }
    elsif (/255.255.255.0/)   { return 24; }
    elsif (/255.255.255.128/) { return 25; }
    elsif (/255.255.255.192/) { return 26; }
    elsif (/255.255.255.224/) { return 27; }
    elsif (/255.255.255.240/) { return 28; }
    elsif (/255.255.255.248/) { return 29; }
    elsif (/255.255.255.252/) { return 30; }
    elsif (/255.255.255.255/) { return 32; }
    else
    {
        return 0;
    }
}
sub finn_prefiks
{
    my $ip = $_[0];
    my $prefiksid = 0;
    if (exists $prefiksid{&and_ip($ip & 255.255.255.252)}{&mask_bits(255.255.255.252)}){
	$prefiksid = $prefiksid{$nettadr}{$maske};
    } elsif (exists $prefiksid{&and_ip($ip & 255.255.255.248)}{&mask_bits(255.255.255.248)}){
	$prefiksid = $prefiksid{$nettadr}{$maske};
    } elsif (exists $prefiksid{&and_ip($ip & 255.255.255.240)}{&mask_bits(255.255.255.240)}){
	$prefiksid = $prefiksid{$nettadr}{$maske};
    } elsif (exists $prefiksid{&and_ip($ip & 255.255.255.224)}{&mask_bits(255.255.255.224)}){
	$prefiksid = $prefiksid{$nettadr}{$maske}; 
    } elsif (exists $prefiksid{&and_ip($ip & 255.255.255.192)}{&mask_bits(255.255.255.192)}){
	$prefiksid = $prefiksid{$nettadr}{$maske}; 
    } elsif (exists $prefiksid{&and_ip($ip & 255.255.255.128)}{&mask_bits(255.255.255.128)}){
	$prefiksid = $prefiksid{$nettadr}{$maske}; 
    } elsif (exists $prefiksid{&and_ip($ip & 255.255.255.0)}{&mask_bits(255.255.255.0)}){
	$prefiksid = $prefiksid{$nettadr}{$maske};
    } elsif (exists $prefiksid{&and_ip($ip & 255.255.254.0)}{&mask_bits(255.255.254.0)}){
	$prefiksid = $prefiksid{$nettadr}{$maske};
    } 
    print "indre prefiksid = $prefiksid\n";
    return $prefiksid;
}
########################
sub hent_prefiksid {
    my $id = "";

    $sql = "SELECT distinct prefiksid,nettadr,maske FROM prefiks";
    $resultat = db_select($sql,$conn);

    while (@line=$resultat->fetchrow)
    {
	@line = map rydd($_), @line;
	$prefiksid{$line[1]}{$line[2]} = $line[0];
    }
} 
################
sub oppdater_en
{
    my $tabell = $_[0];
    my $key = $_[1];
    my $val = $_[2];
    my $nokkel =$_[3];
    my $verdi = $_[4];
    
    if($val){
	my $sql = "UPDATE $tabell SET $key=\'$val\' WHERE $nokkel=\'$verdi\'";
	print $sql;
	&db_execute($sql,$conn);
    }
}


sub db_connect {
    my $db = $_[0];
    my $conn = Pg::connectdb("dbname=$db user=navall password=uka97urgf");
    die $conn->errorMessage unless PGRES_CONNECTION_OK eq $conn->status;
    return $conn;
}

sub db_select {
    my $sql = $_[0];
    my $conn = $_[1];
    my $resultat = $conn->exec($sql);
    die "DATABASEFEIL: $sql\n".$conn->errorMessage
	unless ($resultat->resultStatus eq PGRES_TUPLES_OK);
    return $resultat;
}
sub db_execute {
    my $sql = $_[0];
    my $conn = $_[1];
    my $resultat = $conn->exec($sql);
    die "DATABASEFEIL: $sql\n".$conn->errorMessage
	unless ($resultat->resultStatus eq PGRES_COMMAND_OK);
    return $resultat;
}
sub rydd {    
    if (defined $_[0]) {
	$_ = $_[0];
	s/\s*$//;
	s/^\s*//;
    return $_;
    } else {
	return "";
    }
}

return 1;








