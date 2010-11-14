<?php
header('Content-Type: text/plain');
$config = parse_ini_file('../temperature.conf', $process_sections=true, $scanner_mode=INI_SCANNER_RAW);

$db = mysql_connect($config['mysql']['host'] . ':' . $config['mysql']['port'], $config['mysql']['user'], $config['mysql']['password']);
mysql_select_db($config['mysql']['database'], $db);

$res = mysql_query("SELECT `sensors`.`description` AS `description`, `timestamp`, `temperature`"
                   . " FROM `data`, `sensors`"
                   . " WHERE `sensors`.`id` = `data`.`sensor`"
                   . " AND `temperature` != 85.000000"
                   . " AND `timestamp` >= UNIX_TIMESTAMP() - 3600 * 24;", $db);

$data = array();
while ($arr = mysql_fetch_assoc($res)) {
    if (!isset($data[$arr['description']]))
        $data[$arr['description']] = array();
    $data[$arr['description']][] = array(intval($arr['timestamp']) * 1000, floatval($arr['temperature']));
}

$finaldata = array();
foreach($data as $k => $v)
    $finaldata[] = array('label' => $k, 'data' => $v);

print(json_encode($finaldata));
