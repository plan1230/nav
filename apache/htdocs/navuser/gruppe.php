<table width="100%" class="mainWindow">
<tr><td class="mainWindowHead">
<p><?php echo gettext("Brukergrupper"); ?></p>
</td></tr>

<tr><td>
<?php
include("loginordie.php");
loginOrDie();


echo "<p>";
echo gettext("Her kan du endre og opprette brukergrupper."); 

echo '<p><a href="#nygruppe">';
echo gettext("Legg til ny gruppe");
echo '</a><p>';



if (get_exist('subaction'))
	session_set('gruppesubaction', get_get('subaction'));
if (get_exist('gid'))
	session_set('endregruppeid', get_get('gid') );
if (get_exist('hl'))
	session_set('endregruppehighlight', get_get('hl') );


if (session_get('gruppesubaction') == 'endre') {
	$stekst = gettext("Endre brukergruppe"); 
	$saction = "endregruppe";
} else {
	$stekst = gettext("Legge til brukergruppe");
	$saction = "nygruppe";
}

if (session_get('gruppesubaction') == "nygruppe") {

	print "<h3>" . gettext("Registrerer ny gruppe...") . "</h3>";

	$gid = $dbh->nyBrukerGruppe(post_get('navn'), post_get('descr') );

	if ($gid > 0) { 
		$navn = ""; 	$descr = gettext("Beskrivelse : ");
		
		print "<p><font size=\"+3\">" . gettext("OK</font>, ny brukergruppe er opprettet. Vennligst legg til brukere, utstyrsgrupper og rettigheter til brukergruppen.");

	} else {
    	print "<p><font size=\"+3\">" . gettext("Feil</font>, ny bruker er <b>ikke</b> lagt til i databasen.");
	}
	session_set('gruppesubaction', 'clean');
}

if (session_get('gruppesubaction') == "slett") {

	if (session_get('endregruppeid') > 0) { 
	
		$dbh->slettBrukergruppe( session_get('endregruppeid') );
		print "<p><font size=\"+3\">" . gettext("OK</font>, brukergruppen er slettet fra databasen.");

	} else {
		print "<p><font size=\"+3\">" . gettext("Feil</font>, brukergruppen er <b>ikke</b> slettet.");
	}

	session_set('gruppesubaction', 'clean');
}


if (session_get('gruppesubaction') == "endregruppe") {
	print "<h3>" . gettext("Endrer gruppe...") . "</h3>";

	$dbh->endreBrukergruppe(session_get('endregruppeid'), post_get('navn'), post_get('descr') );
	
	reset ($HTTP_POST_VARS);
	
	while ( list($n, $val) = each ($HTTP_POST_VARS)) {
		if ( preg_match("/bvalg([0-9]+)/i", $n, $m) ) {
			$var = "bvelg" . $m[1];
			$dbh->endreBrukerTilGruppe($m[1], session_get('endregruppeid'), isset(${$var}) );	
		}	
	
		if ( preg_match("/rvalg([0-9]+)/i", $n, $m) ) {
			$var = "rvelg" . $m[1];				
			$dbh->endreRettighet(session_get('endregruppeid'), $m[1], isset(${$var}));
		}
		if ( preg_match("/dvalg([0-9]+)/i", $n, $m) ) {
			$var = "dvelg" . $m[1];		
			$dbh->endreDefault(session_get('endregruppeid'), $m[1], isset(${$var}) );	
		}
	}

	$navn = ""; $descr = gettext("Beskrivelse : ");
	print "<p><font size=\"+3\">" . gettext("OK</font>, endringer foretatt for brukergruppe.");
	
	session_set('gruppesubaction', 'clean');

  
}

$l = new Lister( 103,
	array(gettext('Brukergruppe'), gettext('#brukere'), gettext('#rettighet'), 
		gettext('#std. grupper'), gettext('Valg..') ),
	array(25, 20, 20, 20, 15),
	array('left', 'right', 'right', 'right', 'right' ),
	array(true, true, true, true, false),
	0
);

print "<h3>" . gettext("Brukergrupper") . "</h3>";

if ( get_exist('sortid') )
	$l->setSort(get_get('sort'), get_get('sortid') );
	
$grupper = $dbh->listBrukerGrupper($l->getSort() );

if (session_get('gruppesubaction') == 'endre')
	$l->highlight(session_get('endregruppehighlight'));

for ($i = 0; $i < sizeof($grupper); $i++) {
  
	$valg = '<a href="index.php?subaction=endre&gid=' . $grupper[$i][0] . '&hl=' . $i . '">' .
		'<img alt="Edit" src="icons/edit.gif" border=0></a>&nbsp;' .
    	'<a href="index.php?subaction=slett&gid=' . $grupper[$i][0] . '">' .
    	'<img alt="Delete" src="icons/delete.gif" border=0>' .
    	'</a>';

	if ($grupper[$i][3] > 0 ) { 
		$ab = $grupper[$i][3]; 
	} else { 
		$ab = "<img alt=\"Ingen\" src=\"icons/stop.gif\">"; 
	}

	if ($grupper[$i][4] > 0 ) { 
		$ar = $grupper[$i][4]; 
	} else { 
		$ar = "<img alt=\"Ingen\" src=\"icons/stop.gif\">"; 
	}

	if ($grupper[$i][5] > 0 ) { 
		$ag = $grupper[$i][5]; 
	} else { 
		$ag = "<img alt=\"Ingen\" src=\"icons/stop.gif\">"; 
	}
	
	$l->addElement( array($grupper[$i][1],  // gruppenavn
		$ab,  // #bruekre
		$ar, // #rettigheter
		$ag,  // #std grupper
		$valg
		) 
	);
	
	$inh = new HTMLCell("<p class=\"descr\">" . $grupper[$i][2] . "</p>");	  
	$l->addElement (&$inh);	
	
	
}

print $l->getHTML();

print "<p>[ <a href=\"index.php\">" . gettext("oppdater") . " <img src=\"icons/oppdater.gif\" alt=\"oppdater\" border=0> ]</a> ";
print gettext("Antall grupper: ") . sizeof($grupper);


if (session_get('gruppesubaction') == 'endre') {
	$gr = $dbh->brukergruppeInfo(session_get('endregruppeid') );
	$navn = $gr[0];
	$descr = $gr[1];
} else {
	$descr = gettext("Beskrivelse : ");
}

?>

<a name="nygruppe"></a><p><h3><?php print $stekst; ?></h3>
<form name="form1" method="post" action="index.php?subaction=<?php echo $saction; ?>">
  <table width="100%" border="0" cellspacing="0" cellpadding="3">
    <tr>
      <td width="30%"><p><?php echo gettext("Gruppenavn"); ?></p></td>
      <td width="70%"><input name="navn" type="text" size="40" 
value="<?php echo $navn; ?>"></td>
    </tr>

    <tr>
    	<td colspan="2"><textarea name="descr" cols="60" rows="4">
<?php echo $descr; ?></textarea>  </td>
   	</tr>    
   	
    <tr>
      <td>&nbsp;</td>
      <td align="right">
<?php
print '<input type="submit" name="Submit" value="' . $stekst  . '">';
?>
</td>
    </tr>
  </table>

<?php
if (session_get('gruppesubaction') == 'endre' OR session_get('gruppesubaction') == 'nygruppe') {

	$l = new Lister( 104,
		array(gettext('Valg'), gettext('Bruker'), gettext('Navn') ),
		array(15, 30, 55),
		array('left', 'left', 'left'),
		array(false, true, true),
		2
	);
	
	if ( get_exist('sortid') )
		$l->setSort(get_get('sort'), get_get('sortid') );	
	
	// Henter ut alle brukerene og om de tilhører gruppen eller ikke
	$brukere = $dbh->listGrBrukere(session_get('endregruppeid'), $l->getSort() );
	for ($i = 0; $i < sizeof($brukere); $i++) {
	
		if ($brukere[$i][3] == 't') $medl = " checked"; else $medl = "";
		$velg = '<input name="bvelg' . $brukere[$i][0] . '" type="checkbox" value="1"' . $medl . '>';
		$velg .= '<input name="bvalg' . $brukere[$i][0] . '" value="1" type="hidden">';

		$l->addElement( array(
			$velg,
			$brukere[$i][1],
			$brukere[$i][2],
		) );
		
	}
	print "<h3>" . gettext("Brukere som er medlem i gruppen") . "</h3>";
	print $l->getHTML();

	$l = new Lister( 105,
		array(gettext('Rettighet'), gettext('Default grupper'), gettext('Gruppenavn') ),
		array(15, 15, 70),
		array('left', 'left', 'left'),
		array(false, false, true),
		2
	);

	if ( get_exist('sortid') )
		$l->setSort(get_get('sort'), get_get('sortid') );	

	$utstyr = $dbh->listGrUtstyr(session_get('uid'), session_get('endregruppeid'), $sort);
	for ($i = 0; $i < sizeof($utstyr); $i++) {
	
		if ($utstyr[$i][3] == 't') $r = " checked"; else $r = "";
		$rvelg = '<input name="rvelg' . $utstyr[$i][0] . '" type="checkbox" value="1"' . $r . '>';
		$rvelg .= '<input name="rvalg' . $utstyr[$i][0] . '" value="1" type="hidden">';

		if ($utstyr[$i][4] == 't') $d = " checked"; else $d = "";
		$dvelg = '<input name="dvelg' . $utstyr[$i][0] . '" type="checkbox" value="1"' . $d . '>';
		$dvelg .= '<input name="dvalg' . $utstyr[$i][0] . '" value="1" type="hidden">';

		$l->addElement( array(
			$rvelg,
			$dvelg,			
			$utstyr[$i][1]
		) );
	}
	
	print "<h3>" . gettext("Utstyrsgrupper") . "</h3>";
	print $l->getHTML();
	print '<p><input type="submit" name="Submit" value="' . $stekst  . '">';

}

?>

</form>

</td></tr>
</table>
